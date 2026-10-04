"""
Módulo de extração e transformação de demonstrações contábeis da ANS.

Fluxo:
1. Extrai ZIPs trimestrais (cada um em seu próprio subdiretório)
2. Lê CSVs com dados contábeis
3. Filtra contas de gastos assistenciais
4. Consolida por operadora (soma trimestres)
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


# Padrões para identificar GASTOS ASSISTENCIAIS REAIS
# Estratégia: INCLUIR apenas despesas/sinistros, EXCLUIR receitas e ativos

PATTERNS_GASTOS_ASSISTENCIAIS = [
    r"EVENTOS?\s*/?\s*SINISTROS?\s+CONHECIDOS?\s+OU\s+AVISADOS",
    r"DESPESAS?\s+COM\s+EVENTOS?\s*/?\s*SINISTROS?",
    r"EVENTOS?\s*/?\s*SINISTROS?\s+INDENIZÁVEIS",
    r"PROVIS[ÃA]O\s+DE\s+EVENTOS?\s*/?\s*SINISTROS?\s+A\s+LIQUIDAR",
    r"PROVIS[ÃA]O\s+PARA\s+EVENTOS?\s*/?\s*SINISTROS?\s+OCORRIDOS",
    # ❌ REMOVIDO: r'COBERTURA\s+ASSISTENCIAL',
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
    r"COBERTURA\s+ASSISTENCIAL",  # ← ADICIONAR ESTA LINHA
]

# Manter compatibilidade com código existente
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

            # Limpa subdiretório pra evitar arquivos antigos
            if sub_dir.exists():
                shutil.rmtree(sub_dir)
            sub_dir.mkdir(parents=True)

            logger.info(f"🔓 Extraindo {zip_path.name} → extracted/{stem}/")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(sub_dir)

            # Procura CSV APENAS dentro do subdiretório deste ZIP
            csvs = list(sub_dir.rglob("*.csv"))
            if not csvs:
                logger.warning(f"⚠️  Nenhum CSV encontrado em {zip_path.name}")
                continue

            main_csv = max(csvs, key=lambda p: p.stat().st_size)

            # Normaliza o nome pra <stem>.csv
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
    # FILTRAGEM
    # ------------------------------------------------------------------
    def _filter_gastos_assistenciais(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtra APENAS contas de gastos assistenciais reais.

        Estratégia em duas etapas:
        1. INCLUIR apenas padrões de despesa/sinistro
        2. EXCLUIR contas de receita/ativo/investimento
        """
        df = df.copy()
        df.columns = [c.upper().strip() for c in df.columns]

        df["VL_SALDO_FINAL"] = pd.to_numeric(
            df["VL_SALDO_FINAL"], errors="coerce"
        ).fillna(0)

        descricao = df["DESCRICAO"].fillna("")

        # ETAPA 1: INCLUSÃO - precisa bater com pelo menos 1 padrão de gasto
        mask_inclusao = pd.Series([False] * len(df), index=df.index)
        for pattern in PATTERNS_GASTOS_ASSISTENCIAIS:
            mask_inclusao |= descricao.str.contains(
                pattern, case=False, na=False, regex=True
            )

        # ETAPA 2: EXCLUSÃO - não pode bater com NENHUM padrão de exclusão
        mask_exclusao = pd.Series([False] * len(df), index=df.index)
        for pattern in PATTERNS_EXCLUSAO:
            mask_exclusao |= descricao.str.contains(
                pattern, case=False, na=False, regex=True
            )

        # Filtro final: incluído E NÃO excluído E valor > 0
        mask_final = mask_inclusao & (~mask_exclusao) & (df["VL_SALDO_FINAL"] > 0)

        df_filtered = df[mask_final].copy()

        logger.debug(
            f"🔍 Filtro: {mask_inclusao.sum()} incluídos | "
            f"{mask_exclusao.sum()} excluídos | "
            f"{len(df_filtered)} finais"
        )

        return df_filtered

    # ------------------------------------------------------------------
    # CADOP
    # ------------------------------------------------------------------
    def _load_cadop(self) -> pd.DataFrame:
        """Carrega CADOP e garante colunas REG_ANS e RAZAO_SOCIAL."""
        if not self.cadop_path.exists():
            logger.warning(f"⚠️  CADOP não encontrado em {self.cadop_path}")
            return pd.DataFrame(columns=["REG_ANS", "RAZAO_SOCIAL"])

        # CORREÇÃO: O arquivo usa separator ';'
        configs = [
            {"encoding": "utf-8", "sep": ";"},  # Formato correto
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

        # CORREÇÃO: Mapeamento específico para REGISTRO_OPERADORA
        rename_map = {}

        # Procurar coluna de registro (pode ser REGISTRO_OPERADORA ou REG_ANS)
        for col in df.columns:
            col_upper = col.upper()
            if "REGISTRO" in col_upper or col_upper == "REG_ANS":
                rename_map[col] = "REG_ANS"
                logger.debug(f"🔍 Coluna de registro: '{col}' → REG_ANS")
                break

        # Procurar coluna de razão social
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

        # Aplicar rename
        df = df.rename(columns=rename_map)

        if "RAZAO_SOCIAL" not in df.columns:
            df["RAZAO_SOCIAL"] = "OPERADORA SEM NOME"

        # Selecionar apenas as colunas necessárias
        df_final = df[["REG_ANS", "RAZAO_SOCIAL"]].drop_duplicates(subset=["REG_ANS"])

        logger.success(f"✅ CADOP carregado: {len(df_final)} operadoras")
        return df_final

    # ------------------------------------------------------------------
    # PROCESSAMENTO PRINCIPAL
    # ------------------------------------------------------------------
    def processar_ano(self, ano: int = 2024) -> pd.DataFrame:
        """Processa todos os trimestres e consolida."""
        logger.info(f"🔄 Processando demonstrações contábeis de {ano}...")

        # Step 1: Extrair ZIPs
        csv_files = self.extract_zips(ano)
        if not csv_files:
            raise ValueError("Nenhum CSV extraído")

        # Step 2: Ler e processar cada CSV
        dfs_trimestrais = []

        for csv_path in csv_files:
            trimestre = csv_path.stem  # ex: "1T2024" (nome correto agora!)
            logger.info(f"📊 Processando {trimestre}...")

            df = self._read_csv_demonstracao(csv_path)
            logger.info(f"   Total de linhas: {len(df):,}")

            df_filtered = self._filter_gastos_assistenciais(df)
            logger.info(f"   Gastos assistenciais: {len(df_filtered):,} linhas")

            df_agg = (
                df_filtered.groupby("REG_ANS")["VL_SALDO_FINAL"].sum().reset_index()
            )
            df_agg.columns = ["REG_ANS", f"gasto_{trimestre}"]

            dfs_trimestrais.append(df_agg)

        # Step 3: Consolidar todos os trimestres
        logger.info(f"🔗 Consolidando {len(dfs_trimestrais)} trimestres...")

        consolidated = dfs_trimestrais[0]
        for df_tri in dfs_trimestrais[1:]:
            consolidated = consolidated.merge(df_tri, on="REG_ANS", how="outer")

        consolidated = consolidated.fillna(0)

        gasto_cols = [c for c in consolidated.columns if c.startswith("gasto_")]
        consolidated["gasto_total"] = consolidated[gasto_cols].sum(axis=1)

        # Step 4: Juntar com CADOP
        logger.info("🔗 Juntando com CADOP...")
        cadop = self._load_cadop()

        if cadop.empty:
            logger.warning("⚠️  CADOP vazio, usando nome padrão")
            consolidated["RAZAO_SOCIAL"] = "OPERADORA SEM NOME"
        else:
            # Garante tipos compatíveis pro merge
            consolidated["REG_ANS"] = consolidated["REG_ANS"].astype(str).str.strip()
            cadop = cadop.copy()
            cadop["REG_ANS"] = cadop["REG_ANS"].astype(str).str.strip()

            consolidated = consolidated.merge(cadop, on="REG_ANS", how="left")
            consolidated["RAZAO_SOCIAL"] = consolidated["RAZAO_SOCIAL"].fillna(
                "OPERADORA SEM NOME"
            )

        # Step 5: Reordenar e ordenar
        colunas_finais = ["REG_ANS", "RAZAO_SOCIAL"] + gasto_cols + ["gasto_total"]
        consolidated = consolidated[colunas_finais]
        consolidated = consolidated.sort_values("gasto_total", ascending=False)

        logger.success(f"✅ Consolidação completa: {len(consolidated)} operadoras")
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

        # Top 10
        print("\n" + "=" * 80)
        print("🏆 TOP 10 OPERADORAS POR GASTO ASSISTENCIAL (2024)")
        print("=" * 80)
        for idx, (_, row) in enumerate(df_consolidated.head(10).iterrows(), 1):
            razao = str(row["RAZAO_SOCIAL"])[:50]
            gasto = row["gasto_total"]
            print(f"{idx:>2}. {razao:<50} | R$ {gasto:>15,.2f}")
        print("=" * 80)

        # Estatísticas
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
