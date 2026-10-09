"""API refatorada seguindo princípios REST e boas práticas."""

import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Imports que estavam faltando
from sqlalchemy import create_engine, text

from api.config import get_settings
from api.models import (
    AnalyticsGastosResponse,
    ErrorResponse,
    HealthCheckResponse,
    OperadorasSearchResponse,
    PaginationMetadata,
)
from api.scheduler import start_scheduler, stop_scheduler
from api.services.analytics_service import AnalyticsService
from api.services.operadoras_service import OperadorasService

# Tempo de início para uptime
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup — em testes, os serviços já podem estar pré-injetados no
    # app.state (fixture SQLite); não sobrescrevemos nesse caso.
    settings = get_settings()
    if not hasattr(app.state, "operadoras_service"):
        app.state.operadoras_service = OperadorasService(settings)
    if not hasattr(app.state, "analytics_service"):
        app.state.analytics_service = AnalyticsService(settings)

    # Carrega dados em memória (apenas quando não injetado por teste)
    if getattr(app.state.operadoras_service, "_owns_load", True):
        app.state.operadoras_service.load()

    # Metadata do CADOP para filtros avançados/heat map (F3.4/F3.5)
    try:
        app.state.analytics_service.configure_cadop(app.state.operadoras_service)
    except Exception as e:  # não bloqueia startup
        print(f"⚠ Não foi possível anexar metadata CADOP: {e}")

    start_scheduler()

    yield

    stop_scheduler()
    # Shutdown
    # Cleanup se necessário


# ----------------------------------------------------------------------
# Injeção de dependências — permite que os testes troquem os serviços por
# instâncias com engine SQLite em memória (fixture `client` em conftest).
# ----------------------------------------------------------------------

#: Serviços sob demanda (lazy) usados quando nada é injetado no app.state.
_LAZY: dict = {}


def _operadoras() -> OperadorasService:
    if "operadoras" not in _LAZY:
        _LAZY["operadoras"] = OperadorasService(get_settings())
        _LAZY["operadoras"].load()
    return _LAZY["operadoras"]


def _analytics() -> AnalyticsService:
    if "analytics" not in _LAZY:
        s = get_settings()
        _LAZY["analytics"] = AnalyticsService(s)
        try:
            _LAZY["analytics"].configure_cadop(_operadoras())
        except Exception as e:  # não bloqueia se CADOP estiver indisponível
            print(f"⚠ Metadata CADOP indisponível: {e}")
    return _LAZY["analytics"]


#: Apps que já passaram pelo lifespan e podem ter serviços reais no state.
#: Instâncias criadas por ``create_app()`` nos testes nunca estiveram aqui,
#: então caem direto na factory de teste — nunca no lazy MySQL (bug anterior:
#: o lifespan do app global populava ``_LAZY`` e contaminava as requisições).
_SEEN_APPS: set = set()


def _resolve(request: Request, attr: str, factory):
    """Resolve um serviço: fixture de teste > state injetado > lazy produção."""
    app = request.app
    if app not in _SEEN_APPS:  # instância nova (TestClient) → usa fixture
        mk = getattr(app.state, "_service_factory", None)
        if mk:
            svc = mk(attr)
            if svc is not None:
                setattr(app.state, attr, svc)
                return svc
    st = getattr(app.state, attr, None)
    if st is not None:
        return st
    if attr == "analytics_service":
        return _analytics()
    return _operadoras()


def get_operadoras_service(request: Request) -> OperadorasService:
    """Dependência FastAPI: serviço de operadoras (CADOP)."""
    return _resolve(request, "operadoras_service", _operadoras)


def get_analytics_service(request: Request) -> AnalyticsService:
    """Dependência FastAPI: serviço de analytics."""
    return _resolve(request, "analytics_service", _analytics)


def create_app() -> FastAPI:
    """Factory para criar a aplicação FastAPI."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API REST para consulta de dados da ANS",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    # Admin routes
    from api.admin import router as admin_router

    application.include_router(admin_router)

    # Exception handlers
    @application.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handler para exceções HTTP."""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.__class__.__name__,
                message=exc.detail,
                details=getattr(exc, "details", None),
            ).model_dump(),
        )

    @application.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handler para exceções gerais."""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="InternalServerError",
                message="Erro interno do servidor",
                details={"type": exc.__class__.__name__} if settings.debug else None,
            ).model_dump(),
        )

    return application


app = create_app()
settings = get_settings()


# Health check
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Verifica saúde da aplicação",
)
async def health_check():
    """
    Endpoint de health check com informações detalhadas.

    Retorna status de componentes críticos:
    - Database
    - Cache (se configurado)
    - Uptime
    """
    uptime = time.time() - START_TIME

    # TODO: Implementar checks reais de database e cache
    db_status = "ok"  # Verificar conexão real
    cache_status = "not_configured"

    overall_status = "ok" if db_status == "ok" else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        database=db_status,
        cache=cache_status,
        uptime_seconds=round(uptime, 2),
    )


# Operadoras endpoints
@app.get(
    f"{settings.api_prefix}/analytics/gastos",
    response_model=AnalyticsGastosResponse,
    tags=["Analytics"],
    summary="Ranking de gastos assistenciais",
    responses={
        200: {"description": "Ranking gerado com sucesso"},
        400: {"model": ErrorResponse, "description": "Parâmetros inválidos"},
    },
)
async def get_ranking_gastos(
    periodo: str = Query("2024", description="Período da análise (ano)"),
    top: int = Query(10, ge=1, le=100, description="Quantidade de operadoras no ranking"),
    svc: AnalyticsService = Depends(get_analytics_service),
):
    """
    Retorna ranking das operadoras com maiores gastos assistenciais.

    - **periodo**: Ano de referência (padrão: 2024)
    - **top**: Quantidade de operadoras no ranking (padrão: 10, máximo: 100)
    - **total_operadoras**: Total de operadoras com gastos no período
    - **total_geral**: Soma total de gastos do período (não apenas Top N)

    Análise baseada em dados de demonstrações contábeis consolidadas.
    """

    try:
        # get_top_gastos agora retorna dict com periodo, top, total_geral, total_operadoras, ranking
        dados = svc.get_top_gastos(periodo=periodo, top=top)

        if not dados or not dados.get("ranking"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dados não encontrados para o período {periodo}",
            )

        # Converter dicts para objetos GastoOperadora
        from api.models import GastoOperadora

        ranking_objetos = [GastoOperadora(**item) for item in dados["ranking"]]

        return AnalyticsGastosResponse(
            periodo=dados["periodo"],
            top=dados["top"],
            total_geral=round(dados["total_geral"], 2),
            total_operadoras=dados["total_operadoras"],
            ranking=ranking_objetos,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar dados de analytics: {str(e)}",
        )


@app.get("/api/v1/analytics/year-metadata", tags=["analytics"])
async def year_metadata():
    """
    Retorna metadata de cada ano disponível no banco.
    Usado pelo frontend para mostrar badges (✅ Completo / ⚠️ Parcial / ⚠️ Lacuna ANS).
    """
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    periodo,
                    COUNT(*) as total_operadoras,
                    SUM(gasto_total) as total_geral,
                    SUM(CASE WHEN gasto_1T > 0 THEN 1 ELSE 0 END) as tem_1t,
                    SUM(CASE WHEN gasto_2T > 0 THEN 1 ELSE 0 END) as tem_2t,
                    SUM(CASE WHEN gasto_3T > 0 THEN 1 ELSE 0 END) as tem_3t,
                    SUM(CASE WHEN gasto_4T > 0 THEN 1 ELSE 0 END) as tem_4t
                FROM gastos_assistenciais
                GROUP BY periodo
                ORDER BY periodo
            """))
            rows = result.fetchall()

        # Anos fora do escopo acadêmico (documentado no README)
        EXCLUDED_YEARS = {"2023"}

        metadata = {}
        for row in rows:
            periodo = row[0]
            if periodo in EXCLUDED_YEARS:
                continue

            total_ops = row[1]
            total_geral = float(row[2]) if row[2] else 0

            # Um trimestre é "presente" se >50% das operadoras reportaram
            trimestres_com_dados = sum(
                [
                    1 if (row[3] or 0) > total_ops * 0.5 else 0,
                    1 if (row[4] or 0) > total_ops * 0.5 else 0,
                    1 if (row[5] or 0) > total_ops * 0.5 else 0,
                    1 if (row[6] or 0) > total_ops * 0.5 else 0,
                ]
            )

            metadata[periodo] = {
                "year": periodo,
                "quarters": trimestres_com_dados,
                "total_operadoras": total_ops,
                "total_geral": total_geral,
                "hasAnsgap": periodo == "2024",
            }

        return metadata

    except Exception as e:
        print(f"❌ Erro ao buscar year-metadata: {e}")
        return {}


@app.get(
    f"{settings.api_prefix}/operadoras/{{registro_ans}}",
    response_model=dict,
    tags=["Operadoras"],
    summary="Busca operadora por registro ANS",
    responses={
        200: {"description": "Operadora encontrada"},
        404: {"model": ErrorResponse, "description": "Operadora não encontrada"},
    },
)
async def get_operadora_by_registro(
    registro_ans: str, service: OperadorasService = Depends(get_operadoras_service)
):
    """
    Retorna detalhes de uma operadora específica pelo registro ANS.

    - **registro_ans**: Número de registro ANS da operadora
    """

    # Busca exata pelo registro
    results = service.search(query=registro_ans, limit=1)

    if not results or results[0].registro_ans != registro_ans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operadora com registro ANS '{registro_ans}' não encontrada",
        )

    return results[0].model_dump()


# Endpoint legado para compatibilidade (deprecated)
@app.get(
    "/search",
    deprecated=True,
    tags=["Legacy"],
    summary="[DEPRECATED] Use /api/v1/operadoras",
)
async def legacy_search(
    query: str,
    limit: int = 50,
    service: OperadorasService = Depends(get_operadoras_service),
):
    """Endpoint legado. Use /api/v1/operadoras?q={query}"""
    results = service.search(query=query, limit=limit)
    return {
        "query": query,
        "count": len(results),
        "results": [r.model_dump() for r in results],
    }


@app.get(
    f"{settings.api_prefix}/operadoras",
    response_model=OperadorasSearchResponse,
    tags=["Operadoras"],
    summary="Busca operadoras",
)
async def search_operadoras(
    q: str = Query(..., min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    service: OperadorasService = Depends(get_operadoras_service),
):
    """Busca operadoras por termo."""
    all_results = service.search(query=q, limit=1000)
    total = len(all_results)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated = all_results[start_idx:end_idx]
    total_pages = (total + limit - 1) // limit

    return OperadorasSearchResponse(
        query=q,
        results=paginated,
        metadata=PaginationMetadata(page=page, limit=limit, total=total, pages=total_pages),
    )


# ======================================================================
# v1.2 — Analytics multi-dimensão (F2), análises avançadas (F3),
# exportação/relatórios (F4)
# ======================================================================
from io import BytesIO

from fastapi import File, UploadFile
from fastapi.responses import StreamingResponse

_DIMENSIONS = {"gastos", "financeira", "operacional", "estrutura"}


@app.get(
    f"{settings.api_prefix}/dimension/{{dim}}",
    tags=["Analytics v1.2"],
    summary="Ranking por dimensão contábil (F2.1-F2.3)",
)
async def get_dimension(
    dim: str,
    periodo: str = Query("2024"),
    top: int = Query(20, ge=1, le=100),
    modalidade: Optional[str] = Query(None, description="Filtro CADOP (F3.4)"),
    uf: Optional[str] = Query(None, description="Filtro UF (F3.4)"),
    regiao: Optional[str] = Query(None, description="Filtro região (F3.4)"),
    svc: AnalyticsService = Depends(get_analytics_service),
):
    """Abas Financeira / Operacional / Estrutura com métricas derivadas e badge de outlier."""
    if dim not in _DIMENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dimensão '{dim}' inválida. Válidas: {sorted(_DIMENSIONS)}",
        )
    try:
        return svc.get_dimension(dim, periodo, top=top, modalidade=modalidade, uf=uf, regiao=regiao)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    f"{settings.api_prefix}/top-rankings",
    tags=["Analytics v1.2"],
    summary="Top 20 por receita/sinistro/patrimônio/caixa/lucro (F3.1)",
)
async def get_top_rankings(
    periodo: str = Query("2024"),
    top: int = Query(20, ge=1, le=50),
    svc: AnalyticsService = Depends(get_analytics_service),
):
    return svc.get_top_rankings(periodo=periodo, top=top)


@app.get(
    f"{settings.api_prefix}/quarterly",
    tags=["Analytics v1.2"],
    summary="Análise trimestral 1T×2T×3T×4T (F3.2)",
)
async def get_quarterly(
    periodo: str = Query("2024"),
    registro_ans: Optional[str] = Query(None, description="Drill-down por operadora"),
    svc: AnalyticsService = Depends(get_analytics_service),
):
    return svc.get_quarterly(periodo=periodo, registro_ans=registro_ans)


@app.get(
    f"{settings.api_prefix}/regional",
    tags=["Analytics v1.2"],
    summary="Heat map por UF (F3.5)",
)
async def get_regional(
    periodo: str = Query("2024"),
    metric: str = Query("gasto_total"),
    svc: AnalyticsService = Depends(get_analytics_service),
):
    return svc.get_regional(periodo=periodo, metric=metric)


@app.get(
    f"{settings.api_prefix}/summary",
    tags=["Analytics v1.2"],
    summary="Resumo consolidado do período (dashboard/export)",
)
async def get_summary(
    periodo: str = Query("2024"), svc: AnalyticsService = Depends(get_analytics_service)
):
    return svc.get_summary(periodo=periodo)


@app.get(
    f"{settings.api_prefix}/operadoras/{{registro_ans}}/history",
    tags=["Analytics v1.2"],
    summary="Timeline histórica da operadora (F4.4)",
)
async def get_operadora_history(
    registro_ans: str, svc: AnalyticsService = Depends(get_analytics_service)
):
    data = svc.get_operadora_history(registro_ans)
    if not data["history"]:
        raise HTTPException(
            status_code=404,
            detail=f"Sem histórico para a operadora {registro_ans}",
        )
    return data


def _build_report(svc: AnalyticsService, periodo: str) -> dict:
    a = svc
    return {
        "summary": a.get_summary(periodo),
        "gastos": a.get_top_gastos(periodo=periodo, top=20),
        "financeira": a.get_dimension("financeira", periodo, top=20),
        "operacional": a.get_dimension("operacional", periodo, top=20),
        "estrutura": a.get_dimension("estrutura", periodo, top=20),
        "trimestral": a.get_quarterly(periodo),
        "regional": a.get_regional(periodo),
    }


@app.get(
    f"{settings.api_prefix}/export/pdf",
    tags=["Export (F4)"],
    summary="📥 Exporta relatório PDF institucional (F4.1)",
)
async def export_pdf(
    periodo: str = Query("2024"), svc: AnalyticsService = Depends(get_analytics_service)
):
    from api.services.export.pdf_export import export_pdf as build_pdf

    d = _build_report(svc, periodo)
    try:
        content = build_pdf(
            periodo=periodo,
            summary=d["summary"],
            gastos=d["gastos"],
            financeira=d["financeira"],
            operacional=d["operacional"],
            estrutura=d["estrutura"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {e}")
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ans_intelligence_{periodo}.pdf"'},
    )


@app.get(
    f"{settings.api_prefix}/export/excel",
    tags=["Export (F4)"],
    summary="📥 Exporta .xlsx multi-abas consolidado (F4.2)",
)
async def export_excel(
    periodo: str = Query("2024"), svc: AnalyticsService = Depends(get_analytics_service)
):
    from api.services.export.excel_export import export_excel as build_excel

    d = _build_report(svc, periodo)
    try:
        content = build_excel(
            summary=d["summary"],
            gastos=d["gastos"],
            financeira=d["financeira"],
            operacional=d["operacional"],
            estrutura=d["estrutura"],
            trimestral=d["trimestral"],
            regional=d["regional"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar Excel: {e}")
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="ans_intelligence_{periodo}.xlsx"'},
    )


UPLOAD_DIR = settings.project_root / "etl" / "data" / "uploads"


@app.post(
    f"{settings.api_prefix}/upload-csv",
    tags=["Admin (F4)"],
    summary="Upload manual de CSV histórico (F4.3)",
)
async def upload_csv(
    file: UploadFile = File(...),
    periodo: str = Query("2024", description="Período a importar"),
    dimensao: str = Query("gastos", description="Dimensão do CSV"),
):
    """Recebe um CSV no formato do ETL (REG_ANS, RAZAO_SOCIAL, <colunas>) e o carrega no banco."""
    if dimensao not in _DIMENSIONS:
        raise HTTPException(400, f"Dimensão inválida. Válidas: {sorted(_DIMENSIONS)}")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Apenas arquivos .csv são aceitos")

    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(413, "Arquivo excede o limite de 50MB")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f"manual_{periodo}_{dimensao}.csv"
    dest.write_bytes(raw)

    import pandas as pd

    import etl.load as load_mod

    try:
        df = pd.read_csv(dest, encoding="utf-8", sep=None, engine="python")
        # Resolve a classe pelo MÓDULO em runtime — permite monkeypatch em
        # testes (``etl.load.ANSLoader``) sem quebrar a produção.
        loader = load_mod.ANSLoader()
        df = loader.normalizar_colunas(df, periodo=periodo, dimensao=dimensao)
        n = loader.carregar(df, periodo=periodo, truncate=False)
        return {"status": "ok", "linhas": n, "periodo": periodo, "dimensao": dimensao}
    except Exception as e:
        raise HTTPException(500, f"Falha ao importar CSV: {e}")


# ----------------------------------------------------------------------
# Pós-import: as rotas de negócio deste módulo foram registradas no `app`
# global pelos decorators acima. Passamos a copiá-las para qualquer nova
# instância criada por `create_app()` (usada pelo TestClient dos testes),
# garantindo paridade exata entre o app de produção e o de teste.
# ----------------------------------------------------------------------
#: Rotas de negócio registradas no app global após o import do módulo.
#: Tudo que não for infraestrutura padrão do FastAPI (docs/openapi).
_STANDARD_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
_MODULE_ROUTES = [r for r in app.routes if getattr(r, "path", "") not in _STANDARD_PATHS]


def _copy_module_routes(application: FastAPI) -> None:
    """Re-registra as rotas de negócio em uma nova instância de app.

    Copiar objetos APIRoute diretamente para ``app.routes`` não funciona:
    o roteador só enxerga as rotas da sua própria lista interna e a
    resolução de dependências/serialization precisa ser refeita por app.
    Por isso usamos ``add_api_route`` reaproveitando a função de handler,
    os metadata e a signature original de cada rota.
    """
    existing = {getattr(r, "path", None) for r in application.routes}
    for route in _MODULE_ROUTES:
        path = getattr(route, "path", None)
        if path in existing:
            continue
        methods = set(getattr(route, "methods", {"GET"}) or {"GET"})
        kwargs = dict(
            path=path,
            endpoint=route.endpoint,
            response_model=getattr(route, "response_model", None),
            status_code=getattr(route, "status_code", 200),
            tags=getattr(route, "tags", None),
            summary=getattr(route, "summary", None),
            description=getattr(route, "description", None),
            responses=getattr(route, "responses", None),
            name=getattr(route, "name", None),
            include_in_schema=getattr(route, "include_in_schema", True),
        )
        for m in methods:
            if m in {"HEAD", "OPTIONS", "TRACE"}:
                continue
            try:
                application.add_api_route(
                    path, route.endpoint, methods=[m], **{**kwargs, "path": None}
                )
            except (TypeError, ValueError):
                # Fallback: registra sem metadata opcional problemático
                application.add_api_route(path, route.endpoint, methods=[m])


_create_app_base = create_app


def create_app() -> FastAPI:  # noqa: F811 — wrapper que sincroniza as rotas
    application = _create_app_base()
    if application is not app:
        _copy_module_routes(application)
    return application
