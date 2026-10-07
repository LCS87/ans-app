"""
Módulo de extração e transformação de demonstrações contábeis da ANS.

Fluxo:
1. Extrai ZIPs trimestrais (cada um em seu próprio subdiretório)
2. Lê CSVs com dados contábeis
3. Filtra contas-folha (is_leaf) de eventos/sinistros (411)
4. Consolida por operadora
5. Junta com CADOP para obter razão social
6. Salva CSV consolidado

Uso:
    py -m etl.extract
"""

import shutil
import zipfile
from pathlib import Path
from typing import List
import pandas as pd
from loguru import logger

# ----------------------------------------------------------------------
# CONSTANTES (legado — mantidas para compatibilidade com scripts de
# diagnóstico antigos; o filtro ativo usa is_leaf + prefixo 411)
# ----------------------------------------------------------------------
CODIGOS_DESPESAS_ASSISTENCIAIS = [
    "411",  # Despesas com Eventos/Sinistros (assistenciais)
]

CODIGOS_EXCLUIR = [
    "414",  # Provisão de Eventos/Sinistros (PEONA) - não é despesa realizada
    "46",  # Despesas administrativas (honorários, salários, etc.)
]

PATTERNS_GASTOS_ASSISTENCIAIS = [
    r"EVENTOS?\s*/?\s*SINISTROS?\s+CONHECIDOS?\s+OU\s+AVISADOS",
    r"DESPESAS?\s+COM\s+EVENTOS?\s*/?\s*SINISTROS?",
    r"EVENTOS?\s*/?\s*SINISTROS?\s+INDENIZÁVEIS",
    r"PROVIS[ÃA]O\s+DE\s+EVENTOS?\s*/?\s*SINISTROS?\s+A\s+LIQUIDAR",
    r"PROVIS[ÃA]O\s+PARA\s+EVENTOS?\s*/?\s*SINISTROS?\s+OCORRIDOS",
    r"VARIAÇÃO\s+DA\s+PROVIS[ÃA]O\s+DE\s+EVENTOS",
    r"OUTRAS\s+DESPESAS\s+DE\s+OPERAÇÕES\s+DE\s+PLANOS",
    r"DESPESAS\s+COM\s+OPERAÇÕES\s+DE\s+ASSIST",
]

PATTERNS_EXCLUSAO = [
    r"CONTRAPRESTA[ÇC][ÃA]ES?\s+EMITIDAS?",
    r"PRÊMIOS?\s+EMITIDOS?",
    r"RECEITAS?\s+COM\s+OPERA[ÇC][ÃA]ES?",
    r"OUTRAS\s+RECEITAS?",
    r"CRÉDITOS?\s+DE\s+OPERA[ÇC][ÃA]ES?",
    r"DÉBITOS?\s+DE\s+OPERA[ÇC][ÃA]ES?",
    r"PARTICIPA[ÇC][ÃO]ES?\s+EM\s+OPERADORA",
    r"AQUISI[ÇC][ÃA]O\s+DE\s+CARTEIRA",
    r"F\.?A\.?T\.?E\.?S",
    r"PRÊMIOS?\s+A\s+RECEBER",
    r"CONTRAPRESTA[ÇC][ÃA]O\s+PECUNIÁRIA.*A\s+RECEBER",
    r"PROVIS[ÕO]ES?\s+TÉCNICAS\s+DE\s+OPERA",
    r"VARIAÇÃO\s+DAS?\s+PROVIS[ÕO]ES?\s+TÉCNICAS",
    r"COBERTURA\s+ASSISTENCIAL",
]

KEYWORDS_ASSISTENCIAIS = PATTERNS_GASTOS_ASSISTENCIAIS


class ANSExtractor:
    """Extrator e transformador de dados de demonstrações contábeis."""

    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            base_dir = Path(__file__).parent / "data"

        self.raw_dir = base_dir / "raw" / "demonstracoes"
        self.processed_dir = base_dir / "processed"
        self.cadop_path = base_dir / "raw" / "operadoras_ativas" / "relatorio_cadop.csv"

        self.processed_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # EXTRAÇÃO
    # ------------------------------------------------------------------
    def extract_zips(self, ano: int) -> List[Path]:
        """
        Extrai cada ZIP em seu PRÓPRIO subdiretório.

        Isso evita que CSVs de trimestres diferentes se misturem
        (bug anterior: todos apontavam pro 4T2024.csv).
        """
        ano_dir = self.raw_dir / str(ano)
        extract_base = ano_dir / "extracted"
        extract_base.mkdir(parents=True, exist_ok=True)

        zip_files = sorted(ano_dir.glob("*.zip"))
        if not zip_files:
            raise FileNotFoundError(f"Nenhum ZIP encontrado em {ano_dir}")

        logger.info(f"📦 Extraindo {len(zip_files)} arquivos ZIP de {ano}...")

        csv_files = []
        for zip_path in zip_files:
            stem = zip_path.stem  # ex: "1T2024"
            sub_dir = extract_base / stem

            if sub_dir.exists():
                shutil.rmtree(sub_dir)
            sub_dir.mkdir(parents=True)

            logger.info(f"🔓 Extraindo {zip_path.name} → extracted/{stem}/")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(sub_dir)

            csvs = list(sub_dir.rglob("*.csv"))
            if not csvs:
                logger.warning(f"⚠️  Nenhum CSV encontrado em {zip_path.name}")
                continue

            main_csv = max(csvs, key=lambda p: p.stat().st_size)

            csv_final = sub_dir / f"{stem}.csv"
            if main_csv.resolve() != csv_final.resolve():
                shutil.copy2(main_csv, csv_final)

            logger.success(
                f"✅ {zip_path.name} → {csv_final.name} "
                f"({csv_final.stat().st_size / 1024:.0f} KB)"
            )
            csv_files.append(csv_final)

        return csv_files

    # ------------------------------------------------------------------
    # LEITURA
    # ------------------------------------------------------------------
    def _read_csv_demonstracao(self, csv_path: Path) -> pd.DataFrame:
        """Lê CSV de demonstração contábil com detecção de encoding/separator."""
        configs = [
            {"encoding": "utf-8", "sep": ";"},
            {"encoding": "utf-8", "sep": ","},
            {"encoding": "latin1", "sep": ";"},
            {"encoding": "latin1", "sep": ","},
        ]

        for config in configs:
            try:
                df = pd.read_csv(
                    csv_path,
                    encoding=config["encoding"],
                    sep=config["sep"],
                    on_bad_lines="skip",
                    dtype=str,
                )

                required_cols = ["REG_ANS", "DESCRICAO", "VL_SALDO_FINAL"]
                cols_upper = [c.upper() for c in df.columns]

                if all(col in cols_upper for col in required_cols):
                    logger.debug(
                        f"✅ CSV lido com {config['encoding']} + sep '{config['sep']}'"
                    )
                    return df

            except Exception:
                continue

        raise ValueError(f"Não foi possível ler {csv_path}")

    # ------------------------------------------------------------------
    # CONTAS-FOLHA (is_leaf)
    # ------------------------------------------------------------------
    def marcar_folhas(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Marca is_leaf: conta que NÃO possui filha no mesmo REG_ANS.

        Estratégia vetorizada: ordenando por (REG_ANS, código), uma conta
        é PAI se o próximo código do mesmo REG_ANS começa com ela e é
        mais longo. NaNs são tratados explicitamente.
        """
        df = df.copy()
        df["CD_CONTA_CONTABIL"] = (
            df["CD_CONTA_CONTABIL"].fillna("").astype(str).str.strip()
        )
        df = df.sort_values(["REG_ANS", "CD_CONTA_CONTABIL"], kind="mergesort")

        cur = df["CD_CONTA_CONTABIL"]
        nxt = cur.shift(-1).fillna("")  # ← preenche NaN com string vazia

        mesmo_reg = df["REG_ANS"].eq(df["REG_ANS"].shift(-1)).fillna(False)
        eh_prefixo = nxt.ge(cur + "0") & nxt.lt(cur + ":")

        df["is_leaf"] = ~(mesmo_reg & eh_prefixo)
        return df

    # ------------------------------------------------------------------
    # FILTRAGEM
    # ------------------------------------------------------------------
    def _filter_gastos_assistenciais(self, df: pd.DataFrame) -> pd.DataFrame:
        """Somente contas-folha de eventos/sinistros (411), saldo > 0."""
        df = df.copy()
        df["VL_SALDO_FINAL"] = pd.to_numeric(
            df["VL_SALDO_FINAL"], errors="coerce"
        ).fillna(0)

        df = self.marcar_folhas(df)

        mask = (
            df["is_leaf"]
            & df["CD_CONTA_CONTABIL"].str.startswith("411")
            & (df["VL_SALDO_FINAL"] > 0)
        )

        logger.debug(f"🍃 Folhas: {df['is_leaf'].sum():,} | 411-folha: {mask.sum():,}")
        return df[mask]

    # ------------------------------------------------------------------
    # CADOP
    # ------------------------------------------------------------------
    def _load_cadop(self) -> pd.DataFrame:
        """Carrega CADOP e garante colunas REG_ANS e RAZAO_SOCIAL."""
        if not self.cadop_path.exists():
            logger.warning(f"⚠️  CADOP não encontrado em {self.cadop_path}")
            return pd.DataFrame(columns=["REG_ANS", "RAZAO_SOCIAL"])

        configs = [
            {"encoding": "utf-8", "sep": ";"},
            {"encoding": "latin1", "sep": ";"},
            {"encoding": "utf-8", "sep": ","},
            {"encoding": "latin1", "sep": "\t"},
        ]

        df = None
        for config in configs:
            try:
                df = pd.read_csv(
                    self.cadop_path,
                    encoding=config["encoding"],
                    sep=config["sep"],
                    on_bad_lines="skip",
                    dtype=str,
                )
                if len(df.columns) > 1:
                    logger.debug(
                        f"✅ CADOP lido com {config['encoding']} + sep '{config['sep']}'"
                    )
                    break
            except Exception:
                continue

        if df is None or df.empty:
            logger.error("❌ Não foi possível ler CADOP")
            return pd.DataFrame(columns=["REG_ANS", "RAZAO_SOCIAL"])

        df.columns = [str(c).strip() for c in df.columns]
        logger.debug(f"📋 Colunas do CADOP: {list(df.columns)[:5]}...")

        rename_map = {}

        for col in df.columns:
            col_upper = col.upper()
            if "REGISTRO" in col_upper or col_upper == "REG_ANS":
                rename_map[col] = "REG_ANS"
                logger.debug(f"🔍 Coluna de registro: '{col}' → REG_ANS")
                break

        for col in df.columns:
            col_upper = col.upper()
            if "RAZAO" in col_upper or col_upper == "RAZAO_SOCIAL":
                rename_map[col] = "RAZAO_SOCIAL"
                logger.debug(f"🔍 Coluna de razão social: '{col}' → RAZAO_SOCIAL")
                break

        if "REG_ANS" not in rename_map.values():
            logger.error(
                f"❌ Coluna REG_ANS não encontrada. Colunas: {list(df.columns)}"
            )
            return pd.DataFrame(columns=["REG_ANS", "RAZAO_SOCIAL"])

        df = df.rename(columns=rename_map)

        if "RAZAO_SOCIAL" not in df.columns:
            df["RAZAO_SOCIAL"] = "OPERADORA SEM NOME"

        df_final = df[["REG_ANS", "RAZAO_SOCIAL"]].drop_duplicates(subset=["REG_ANS"])

        logger.success(f"✅ CADOP carregado: {len(df_final)} operadoras")
        return df_final

    # ------------------------------------------------------------------
    # PROCESSAMENTO PRINCIPAL
    # ------------------------------------------------------------------
    def processar_ano(self, ano: int = 2024) -> pd.DataFrame:
        """
        Processa todos os trimestres e consolida usando MÉTODO D (híbrido).

        Metodologia:
        1. Para cada conta no ramo 41, pega o último valor não-zero
        2. Identifica raízes (contas sem ancestral com valor)
        3. Para cada raiz:
           - Se tem folhas descendentes que cobrem ≥90% do valor → usa folhas
           - Se folhas > raiz → usa folhas (raiz subdeclarada)
           - Senão → usa raiz (folhas incompletas ou inexistentes)

        Resultado: sem dupla contagem, sem perder sintéticas, sem descartar negativos.
        """
        logger.info(f"🔄 Processando demonstrações contábeis de {ano}...")

        csv_files = self.extract_zips(ano)
        if not csv_files:
            raise ValueError("Nenhum CSV extraído")

        # Ler todos os trimestres
        dfs = []
        for csv_path in csv_files:
            trimestre = csv_path.stem
            logger.info(f"📊 Lendo {trimestre}...")

            df = self._read_csv_demonstracao(csv_path)
            df["TRIMESTRE"] = trimestre
            dfs.append(df)

        df_all = pd.concat(dfs, ignore_index=True)
        logger.info(f"📊 Total de linhas: {len(df_all):,}")

        # Filtrar ramo 41 (EVENTOS INDENIZÁVEIS / SINISTROS)
        df_all["CD_CONTA_CONTABIL"] = df_all["CD_CONTA_CONTABIL"].fillna("").str.strip()
        df_all["VL_SALDO_FINAL"] = pd.to_numeric(
            df_all["VL_SALDO_FINAL"], errors="coerce"
        ).fillna(0)

        df_ramo = df_all[df_all["CD_CONTA_CONTABIL"].str.startswith("41")].copy()
        logger.info(f"🌳 Ramo 41: {len(df_ramo):,} registros")

        # Passo 1: último valor não-zero por (REG_ANS, conta)
        df_nz = df_ramo[df_ramo["VL_SALDO_FINAL"] != 0]
        df_last = (
            df_nz.sort_values("TRIMESTRE")
            .groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False)
            .tail(1)
        )
        logger.info(f"📊 Contas com valor: {len(df_last):,}")

        # Passo 2: aplicar Método D por operadora
        resultados = {}
        for reg, grupo in df_last.groupby("REG_ANS"):
            contas = grupo["CD_CONTA_CONTABIL"].tolist()
            valores = dict(zip(contas, grupo["VL_SALDO_FINAL"]))
            contas_set = set(contas)

            # Identificar raízes (sem ancestral com valor)
            raizes = [
                c
                for c in contas
                if not any(c[:L] in contas_set for L in range(1, len(c)))
            ]

            # Calcular total usando Método D
            total = 0.0
            for raiz in raizes:
                # Encontrar folhas descendentes
                folhas_desc = [
                    c
                    for c in contas
                    if c != raiz
                    and c.startswith(raiz)
                    and not any(
                        c[:L] in contas_set for L in range(len(raiz) + 1, len(c))
                    )
                ]

                if not folhas_desc:
                    # Raiz sem folhas: usa o próprio valor (±)
                    total += valores[raiz]
                else:
                    soma_folhas = sum(valores[f] for f in folhas_desc)
                    if (
                        soma_folhas >= 0.9 * valores[raiz]
                        or soma_folhas > valores[raiz]
                    ):
                        # Folhas cobrem bem ou superam a raiz
                        total += soma_folhas
                    else:
                        # Folhas incompletas: usa raiz
                        total += valores[raiz]

            resultados[reg] = total

        consolidated = pd.DataFrame(
            [
                {"REG_ANS": reg, "gasto_total": valor}
                for reg, valor in resultados.items()
            ]
        )
        logger.info(f"🌱 Operadoras com valor: {len(consolidated):,}")

        # Também calcular soma por trimestre (para histórico)
        gasto_cols = []
        for trimestre in sorted(df_all["TRIMESTRE"].unique()):
            df_tri = df_all[df_all["TRIMESTRE"] == trimestre]
            df_tri_ramo = df_tri[df_tri["CD_CONTA_CONTABIL"].str.startswith("41")]
            df_tri_nz = df_tri_ramo[df_tri_ramo["VL_SALDO_FINAL"] != 0]

            # Aplicar Método D para este trimestre
            resultados_tri = {}
            for reg, grupo in df_tri_nz.groupby("REG_ANS"):
                contas = grupo["CD_CONTA_CONTABIL"].tolist()
                valores = dict(zip(contas, grupo["VL_SALDO_FINAL"]))
                contas_set = set(contas)

                raizes = [
                    c
                    for c in contas
                    if not any(c[:L] in contas_set for L in range(1, len(c)))
                ]

                total = 0.0
                for raiz in raizes:
                    folhas_desc = [
                        c
                        for c in contas
                        if c != raiz
                        and c.startswith(raiz)
                        and not any(
                            c[:L] in contas_set for L in range(len(raiz) + 1, len(c))
                        )
                    ]

                    if not folhas_desc:
                        total += valores[raiz]
                    else:
                        soma_folhas = sum(valores[f] for f in folhas_desc)
                        if (
                            soma_folhas >= 0.9 * valores[raiz]
                            or soma_folhas > valores[raiz]
                        ):
                            total += soma_folhas
                        else:
                            total += valores[raiz]

                resultados_tri[reg] = total

            if resultados_tri:
                df_tri_agg = pd.DataFrame(
                    [
                        {"REG_ANS": reg, f"gasto_{trimestre}": valor}
                        for reg, valor in resultados_tri.items()
                    ]
                )
                consolidated = consolidated.merge(df_tri_agg, on="REG_ANS", how="left")
                gasto_cols.append(f"gasto_{trimestre}")

        consolidated = consolidated.fillna(0)

        # Juntar com CADOP
        logger.info("🔗 Juntando com CADOP...")
        cadop = self._load_cadop()

        if cadop.empty:
            logger.warning("⚠️  CADOP vazio, usando nome padrão")
            consolidated["RAZAO_SOCIAL"] = "OPERADORA SEM NOME"
        else:
            consolidated["REG_ANS"] = consolidated["REG_ANS"].astype(str).str.strip()
            cadop = cadop.copy()
            cadop["REG_ANS"] = cadop["REG_ANS"].astype(str).str.strip()

            consolidated = consolidated.merge(cadop, on="REG_ANS", how="left")
            consolidated["RAZAO_SOCIAL"] = consolidated["RAZAO_SOCIAL"].fillna(
                "OPERADORA SEM NOME"
            )

        # Reordenar colunas
        colunas_finais = ["REG_ANS", "RAZAO_SOCIAL"] + gasto_cols + ["gasto_total"]
        consolidated = consolidated[colunas_finais]
        consolidated = consolidated.sort_values("gasto_total", ascending=False)

        total = consolidated["gasto_total"].sum()
        logger.success(
            f"✅ Consolidação completa: {len(consolidated)} operadoras | "
            f"R$ {total:,.0f} (Método D - híbrido)"
        )
        return consolidated

    # ------------------------------------------------------------------
    # SAÍDA
    # ------------------------------------------------------------------
    def salvar_csv(self, df: pd.DataFrame, ano: int) -> Path:
        """Salva DataFrame consolidado em CSV."""
        output_path = self.processed_dir / f"gastos_assistenciais_{ano}.csv"

        df.to_csv(output_path, index=False, encoding="utf-8")

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.success(f"💾 CSV salvo: {output_path} ({file_size_mb:.2f} MB)")

        return output_path


async def main():
    """Função principal para execução standalone."""
    extractor = ANSExtractor()

    try:
        df_consolidated = extractor.processar_ano(2024)
        extractor.salvar_csv(df_consolidated, 2024)

        print("\n" + "=" * 80)
        print("🏆 TOP 10 OPERADORAS POR GASTO ASSISTENCIAL (2024)")
        print("=" * 80)
        for idx, (_, row) in enumerate(df_consolidated.head(10).iterrows(), 1):
            razao = str(row["RAZAO_SOCIAL"])[:50]
            gasto = row["gasto_total"]
            print(f"{idx:>2}. {razao:<50} | R$ {gasto:>15,.2f}")
        print("=" * 80)

        total = df_consolidated["gasto_total"].sum()
        print(f"\n📊 ESTATÍSTICAS")
        print(f"   Total de operadoras: {len(df_consolidated):,}")
        print(f"   Gasto total 2024: R$ {total:,.2f}")
        print(
            f"   Média por operadora: R$ {df_consolidated['gasto_total'].mean():,.2f}"
        )
        print(f"   Mediana: R$ {df_consolidated['gasto_total'].median():,.2f}")
        print("=" * 80)

    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
