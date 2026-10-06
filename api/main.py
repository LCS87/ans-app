"""API refatorada seguindo princípios REST e boas práticas."""

import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.scheduler import start_scheduler, stop_scheduler
from api.config import get_settings, Settings
from api.models import (
    OperadorasSearchResponse,
    AnalyticsGastosResponse,
    HealthCheckResponse,
    ErrorResponse,
    PaginationMetadata,
)
from api.services.operadoras_service import OperadorasService
from api.services.analytics_service import AnalyticsService

# Tempo de início para uptime
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup
    settings = get_settings()
    app.state.operadoras_service = OperadorasService(settings)
    app.state.analytics_service = AnalyticsService(settings)

    # Carrega dados em memória
    app.state.operadoras_service.load()

    start_scheduler()

    yield

    stop_scheduler()
    # Shutdown
    # Cleanup se necessário


def create_app() -> FastAPI:
    """Factory para criar a aplicação FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API REST para consulta de dados da ANS",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    # Admin routes (ADICIONA ISSO)
    from api.admin import router as admin_router

    app.include_router(admin_router)

    return app


app = create_app()
settings = get_settings()


# Exception handlers
@app.exception_handler(HTTPException)
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


@app.exception_handler(Exception)
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
    top: int = Query(
        10, ge=1, le=100, description="Quantidade de operadoras no ranking"
    ),
):
    """
    Retorna ranking das operadoras com maiores gastos assistenciais.

    - **periodo**: Ano de referência (padrão: 2024)
    - **top**: Quantidade de operadoras no ranking (padrão: 10, máximo: 100)
    - **total_operadoras**: Total de operadoras com gastos no período
    - **total_geral**: Soma total de gastos do período (não apenas Top N)

    Análise baseada em dados de demonstrações contábeis consolidadas.
    """
    service: AnalyticsService = app.state.analytics_service

    try:
        # get_top_gastos agora retorna dict com periodo, top, total_geral, total_operadoras, ranking
        dados = service.get_top_gastos(periodo=periodo, top=top)

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
async def get_operadora_by_registro(registro_ans: str):
    """
    Retorna detalhes de uma operadora específica pelo registro ANS.

    - **registro_ans**: Número de registro ANS da operadora
    """
    service: OperadorasService = app.state.operadoras_service

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
async def legacy_search(query: str, limit: int = 50):
    """Endpoint legado. Use /api/v1/operadoras?q={query}"""
    service: OperadorasService = app.state.operadoras_service
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
):
    """Busca operadoras por termo."""
    service: OperadorasService = app.state.operadoras_service
    all_results = service.search(query=q, limit=1000)
    total = len(all_results)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated = all_results[start_idx:end_idx]
    total_pages = (total + limit - 1) // limit

    return OperadorasSearchResponse(
        query=q,
        results=paginated,
        metadata=PaginationMetadata(
            page=page, limit=limit, total=total, pages=total_pages
        ),
    )
