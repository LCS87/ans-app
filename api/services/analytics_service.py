"""Serviço de analytics e relatórios - Versão com MySQL (v1.2 multi-dimensão)."""

from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text

from api.accounting_maps import get_dimension
from api.config import Settings


class AnalyticsService:
    """Serviço para analytics e relatórios usando MySQL."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
        )
        # Metadata CADOP ({registro_ans: {uf, regiao, modalidade}}) — F3.4/F3.5
        self.cadop_meta: dict = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def configure_cadop(self, operadoras_service) -> int:
        """Anexa metadata do CADOP (UF/região/modalidade) para filtros e heat map."""
        meta = {}
        for op in operadoras_service.get_all():
            reg = str(op.get("registro_ans", "")).strip()
            if reg:
                meta[reg] = {
                    "uf": op.get("uf") or op.get("u") or "",
                    "regiao": op.get("regiao_comercializacao") or "",
                    "modalidade": op.get("modalidade") or "",
                }
        self.cadop_meta = meta
        return len(meta)

    def _query_df(self, sql: str, params: dict) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)

    def _apply_filters(
        self, df: pd.DataFrame, modalidade=None, uf=None, regiao=None
    ) -> pd.DataFrame:
        """Aplica filtros avançados (F3.4) via metadata CADOP."""
        if not self.cadop_meta or df.empty:
            return df
        meta = self.cadop_meta

        def _get(reg, key):
            return meta.get(str(reg), {}).get(key, "")

        if modalidade:
            df = df[df["registro_ans"].map(lambda r: _get(r, "modalidade")) == modalidade]
        if uf:
            df = df[df["registro_ans"].map(lambda r: _get(r, "uf")) == uf.upper()]
        if regiao:
            df = df[df["registro_ans"].map(lambda r: _get(r, "regiao").upper()) == regiao.upper()]
        return df.reset_index(drop=True)

    @staticmethod
    def _detect_outliers(df: pd.DataFrame, col: str) -> list:
        """Badge ⚠️ Outlier (F3.3): IQR com cerca de 1,5×IQR acima do Q3.

        Para amostras pequenas (<8), o guardrail 'porte' usa mediana × 4 —
        operadora 4x acima da mediana do recorte é estatisticamente fora
        da curva mesmo sem quartis estáveis.
        """
        if df.empty or col not in df.columns:
            return [False] * len(df)
        s = df[col].astype(float)
        if len(df) >= 8:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            return [(v < lo) or (v > hi) for v in s]
        # Amostra pequena: regra robusta por mediana (guardrail de porte)
        med = s.median()
        hi = med * 4 if med > 0 else s.max() + 1
        return [bool(v > hi) for v in s]

    def get_top_gastos(self, periodo: str, top: int = 10) -> dict:
        """
        Retorna ranking de operadoras com maiores gastos.

        Agora também retorna total_operadoras do período.
        """
        try:
            with self.engine.connect() as conn:
                # Buscar ranking
                result = conn.execute(
                    text("""
                        SELECT registro_ans, razao_social, gasto_total
                        FROM gastos_assistenciais
                        WHERE periodo = :periodo
                        ORDER BY gasto_total DESC
                        LIMIT :limit
                    """),
                    {"periodo": periodo, "limit": top},
                )
                rows = result.fetchall()

                # Contar total de operadoras no período
                result_count = conn.execute(
                    text("""
                        SELECT COUNT(*) as total, SUM(gasto_total) as soma
                        FROM gastos_assistenciais
                        WHERE periodo = :periodo
                    """),
                    {"periodo": periodo},
                )
                stats = result_count.fetchone()
                total_operadoras = stats[0] if stats else 0
                total_geral = float(stats[1]) if stats and stats[1] else 0

                if not rows:
                    print(f"⚠ Nenhum dado para período {periodo}, usando exemplo")
                    return self._get_example_data(top, periodo)

                ranking = []
                for idx, row in enumerate(rows, 1):
                    ranking.append(
                        {
                            "posicao": idx,
                            "registro_ans": str(row[0]),
                            "razao_social": str(row[1]),
                            "valor_total": float(row[2]),
                        }
                    )

                return {
                    "periodo": periodo,
                    "top": top,
                    "total_geral": total_geral,
                    "total_operadoras": total_operadoras,
                    "ranking": ranking,
                }

        except Exception as e:
            print(f"✗ Erro ao consultar MySQL: {e}")
            return self._get_example_data(top, periodo)

    def _get_example_data(self, top: int, periodo: str) -> dict:
        """Fallback vazio quando não há dados no banco."""
        return {
            "periodo": periodo,
            "top": top,
            "total_geral": 0,
            "total_operadoras": 0,
            "ranking": [],
        }

    # ------------------------------------------------------------------
    # F2.1-F2.3 — Dimensões contábeis (Financeira / Operacional / Estrutura)
    # ------------------------------------------------------------------
    def get_dimension(
        self,
        dimension: str,
        periodo: str,
        top: int = 20,
        modalidade: Optional[str] = None,
        uf: Optional[str] = None,
        regiao: Optional[str] = None,
    ) -> dict:
        """Ranking de uma dimensão contábil com agregados derivados e outliers."""
        dim = get_dimension(dimension)
        db_cols = sorted(set(dim["columns"].keys()))
        select_cols = ["registro_ans", "razao_social"] + db_cols
        sql = f"""
            SELECT {", ".join(select_cols)}
            FROM gastos_assistenciais
            WHERE periodo = :periodo
        """
        df = self._query_df(sql, {"periodo": periodo})
        df = self._apply_filters(df, modalidade=modalidade, uf=uf, regiao=regiao)

        for c in db_cols:
            if c not in df.columns:
                df[c] = 0.0
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

        # Derivadas somativas (ex.: dividas = 21 + 23)
        for nome, (a, b) in dim.get("derived", {}).items():
            df[nome] = df.get(a, 0.0) + df.get(b, 0.0)

        # Agregados proporcionais (sinistralidade, endividamento)
        for nome, (num, den) in dim.get("aggregates", {}).items():
            d = df[den] if den in df.columns else pd.Series(0.0, index=df.index)
            n = df[num] if num in df.columns else pd.Series(0.0, index=df.index)
            df[nome] = (n / d.where(d != 0)).fillna(0.0).clip(-5, 5)

        sort_col = dim.get("sort_by", db_cols[0])
        df = df.sort_values(sort_col, ascending=False).head(top).reset_index(drop=True)

        outliers = self._detect_outliers(df, sort_col)
        rows = []
        for i, r in df.iterrows():
            row = {
                "posicao": i + 1,
                "registro_ans": str(r["registro_ans"]),
                "razao_social": str(r["razao_social"]),
                "valores": {c: round(float(r[c]), 2) for c in db_cols},
                "agregados": {a: round(float(r[a]), 4) for a in dim.get("aggregates", {})},
                "outlier": bool(outliers[i]),
            }
            meta = self.cadop_meta.get(row["registro_ans"], {})
            row["uf"] = meta.get("uf") or None
            row["regiao"] = meta.get("regiao") or None
            row["modalidade"] = meta.get("modalidade") or None
            rows.append(row)

        return {
            "dimension": dimension,
            "label": dim["label"],
            "icon": dim["icon"],
            "periodo": periodo,
            "total_operadoras": int(len(df)),
            "totais": {c: round(float(self._safe_sum(c, periodo)), 2) for c in db_cols},
            "ranking": rows,
        }

    def _safe_sum(self, col: str, periodo: str) -> float:
        try:
            with self.engine.connect() as conn:
                v = conn.execute(
                    text(f"SELECT SUM(`{col}`) FROM gastos_assistenciais WHERE periodo = :p"),
                    {"p": periodo},
                ).fetchone()[0]
            return float(v or 0)
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # F3.1 — Top rankings multi-métrica
    # ------------------------------------------------------------------
    TOP_METRICS = {
        "receita": "receita",
        "sinistro": "gasto_total",
        "patrimonio": "patrimonio",
        "caixa": "caixa",
        "lucro": "lucro",
    }

    def get_top_rankings(self, periodo: str, top: int = 20) -> dict:
        """5 sub-rankings (receita, sinistro, patrimônio, caixa, lucro)."""
        out = {}
        for name, col in self.TOP_METRICS.items():
            sql = f"""
                SELECT registro_ans, razao_social, `{col}` AS valor
                FROM gastos_assistenciais
                WHERE periodo = :periodo AND `{col}` > 0
                ORDER BY `{col}` DESC
                LIMIT :limit
            """
            rows = self._query_df(sql, {"periodo": periodo, "limit": top})
            out[name] = [
                {
                    "posicao": i + 1,
                    "registro_ans": str(r["registro_ans"]),
                    "razao_social": str(r["razao_social"]),
                    "valor": round(float(r["valor"]), 2),
                }
                for i, r in rows.iterrows()
            ]
        return {"periodo": periodo, "top": top, "rankings": out}

    # ------------------------------------------------------------------
    # F3.2 — Análise trimestral
    # ------------------------------------------------------------------
    def get_quarterly(self, periodo: str, registro_ans: Optional[str] = None) -> dict:
        """Drill-down temporal 1T × 2T × 3T × 4T (por operadora ou consolidado)."""
        quarters = ["gasto_1T", "gasto_2T", "gasto_3T", "gasto_4T"]
        if registro_ans:
            sql = """
                SELECT registro_ans, razao_social, gasto_1T, gasto_2T,
                       gasto_3T, gasto_4T, gasto_total
                FROM gastos_assistenciais
                WHERE periodo = :periodo AND registro_ans = :reg
            """
            df = self._query_df(sql, {"periodo": periodo, "reg": registro_ans})
        else:
            # Retorna consolidado + top 20 operadoras individuais
            sql_total = f"""
                SELECT 'TOTAL' AS registro_ans, 'Consolidado' AS razao_social,
                       {', '.join(f'SUM(`{q}`) AS `{q}`' for q in quarters)},
                       SUM(gasto_total) AS gasto_total
                FROM gastos_assistenciais WHERE periodo = :periodo
            """
            df_total = self._query_df(sql_total, {"periodo": periodo})

            sql_ops = """
                SELECT registro_ans, razao_social, gasto_1T, gasto_2T,
                       gasto_3T, gasto_4T, gasto_total
                FROM gastos_assistenciais
                WHERE periodo = :periodo AND gasto_total > 0
                ORDER BY gasto_total DESC
                LIMIT 20
            """
            df_ops = self._query_df(sql_ops, {"periodo": periodo})
            df = pd.concat([df_total, df_ops], ignore_index=True)

        series = []
        for _, r in df.iterrows():
            series.append(
                {
                    "registro_ans": str(r["registro_ans"]),
                    "razao_social": str(r["razao_social"]),
                    "trimestres": {
                        q.replace("gasto_", ""): round(float(r[q] or 0), 2) for q in quarters
                    },
                    "total": round(float(r["gasto_total"] or 0), 2),
                }
            )
        return {"periodo": periodo, "series": series}

    # ------------------------------------------------------------------
    # F3.5 — Comparação regional (heat map por UF)
    # ------------------------------------------------------------------
    # Mapeamento de código de região CADOP → nome legível
    _REGIAO_MAP = {
        "1": "Norte", "2": "Nordeste", "3": "Centro-Oeste",
        "4": "Sul", "5": "Sudeste",
        # Variantes por nome completo (caso o CADOP retorne nome)
        "Norte": "Norte", "Nordeste": "Nordeste", "Centro-Oeste": "Centro-Oeste",
        "Sul": "Sul", "Sudeste": "Sudeste",
    }

    # Mapeamento UF → região (fallback quando CADOP não tem)
    _UF_REGIAO = {
        "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte",
        "RO": "Norte", "RR": "Norte", "TO": "Norte",
        "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
        "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
        "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
        "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
        "PR": "Sul", "RS": "Sul", "SC": "Sul",
    }

    def get_regional(self, periodo: str, metric: str = "gasto_total") -> dict:
        """Agrega métrica por UF usando metadata CADOP (heat map Brasil)."""
        safe_metric = (
            metric
            if metric
            in {
                "gasto_total",
                "receita",
                "lucro",
                "caixa",
                "patrimonio",
                "despesas_administrativas",
            }
            else "gasto_total"
        )
        sql = f"""
            SELECT registro_ans, razao_social, `{safe_metric}` AS valor
            FROM gastos_assistenciais WHERE periodo = :periodo
        """
        df = self._query_df(sql, {"periodo": periodo})
        agg: dict = {}
        for _, r in df.iterrows():
            uf = self.cadop_meta.get(str(r["registro_ans"]), {}).get("uf", "") or "--"
            uf = uf.upper().strip()
            # Resolve nome da região: CADOP pode retornar código ou nome
            regiao_raw = self.cadop_meta.get(str(r["registro_ans"]), {}).get("regiao", "") or ""
            regiao = self._REGIAO_MAP.get(str(regiao_raw).strip(), "") or self._UF_REGIAO.get(uf, "")
            e = agg.setdefault(
                uf,
                {
                    "uf": uf,
                    "regiao": regiao,
                    "operadoras": 0,
                    "valor": 0.0,
                },
            )
            # Garante que a região fica preenchida caso a primeira entrada estivesse vazia
            if not e["regiao"] and regiao:
                e["regiao"] = regiao
            e["operadoras"] += 1
            e["valor"] += float(r["valor"] or 0)
        items = sorted(agg.values(), key=lambda x: -x["valor"])
        for it in items:
            it["valor"] = round(it["valor"], 2)
        return {"periodo": periodo, "metric": safe_metric, "ufs": items}

    # ------------------------------------------------------------------
    # Resumo geral para PDF/Excel/dashboard (F4)
    # ------------------------------------------------------------------
    def get_summary(self, periodo: str) -> dict:
        gastos = self.get_top_gastos(periodo=periodo, top=10)
        fin = self.get_dimension("financeira", periodo, top=10)
        ops = self.get_quarterly(periodo)
        return {
            "periodo": periodo,
            "gastos": gastos,
            "financeiro": fin,
            "trimestral": ops,
        }

    # ------------------------------------------------------------------
    # F4.4 — Timeline histórica por operadora
    # ------------------------------------------------------------------
    def get_operadora_history(self, registro_ans: str) -> dict:
        sql = """
            SELECT periodo, razao_social, gasto_total, receita, lucro,
                   patrimonio, caixa, despesas_administrativas
            FROM gastos_assistenciais
            WHERE registro_ans = :reg
            ORDER BY periodo
        """
        df = self._query_df(sql, {"reg": registro_ans})
        history = [
            {
                "periodo": str(r["periodo"]),
                "razao_social": str(r["razao_social"]),
                "gasto_total": round(float(r["gasto_total"] or 0), 2),
                "receita": round(float(r["receita"] or 0), 2),
                "lucro": round(float(r["lucro"] or 0), 2),
                "patrimonio": round(float(r["patrimonio"] or 0), 2),
                "caixa": round(float(r["caixa"] or 0), 2),
                "despesas_administrativas": round(float(r["despesas_administrativas"] or 0), 2),
            }
            for _, r in df.iterrows()
        ]
        meta = self.cadop_meta.get(registro_ans, {})
        return {
            "registro_ans": registro_ans,
            "uf": meta.get("uf") or None,
            "modalidade": meta.get("modalidade") or None,
            "history": history,
        }
