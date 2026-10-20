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
import time
import zipfile
from pathlib import Path
from typing import List

import pandas as pd
from loguru import logger

from etl.normalization import (
    deduplicar_contas,
    normalizar_serie_registro_ans,
    parse_serie_valor_brl,
)

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

    # Colunas do CADOP usadas para popular a tabela ``operadoras``.
    CADOP_CAMPOS = {
        "CNPJ": "cnpj",
        "NOME_FANTASIA": "nome_fantasia",
        "MODALIDADE": "modalidade",
        "LOGRADOURO": "logradouro",
        "NUMERO": "numero",
        "COMPLEMENTO": "complemento",
        "BAIRRO": "bairro",
        "CIDADE": "cidade",
        "UF": "uf",
        "CEP": "cep",
        "DDD": "ddd",
        "TELEFONE": "telefone",
        "FAX": "fax",
        "ENDERECO_ELETRONICO": "endereco_eletronico",
        "REPRESENTANTE": "representante",
        "CARGO_REPRESENTANTE": "cargo_representante",
        "REGIAO_DE_COMERCIALIZACAO": "regiao_comercializacao",
        "DATA_REGISTRO_ANS": "data_registro_ans",
    }

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
    def _read_csv_demonstracao(
        self, csv_path: Path, *, parse_numerico: bool = False
    ) -> pd.DataFrame:
        """Lê CSV de demonstração contábil com detecção de encoding/separator.

        ``parse_numerico=True`` faz o pandas converter ``VL_SALDO_FINAL``
        diretamente (decimal=',', milhar='.') e lê apenas as colunas usadas
        pelo ETL. Isso evita manter milhões de strings em memória durante o
        reload. O fallback mantém a leitura como string para layouts
        inesperados.
        """
        configs = [
            {"encoding": "utf-8", "sep": ";"},
            {"encoding": "utf-8", "sep": ","},
            {"encoding": "latin1", "sep": ";"},
            {"encoding": "latin1", "sep": ","},
        ]
        colunas_uteis = {
            "REG_ANS",
            "CD_CONTA_CONTABIL",
            "DESCRICAO",
            "VL_SALDO_FINAL",
            "DATA",
        }

        # No Windows, o antivírus/antivirus service pode segurar o arquivo
        # logo após a extração do ZIP. Duas tentativas evitam abortar o
        # pipeline por um bloqueio transitório de I/O.
        for tentativa in range(2):
            for config in configs:
                try:
                    kwargs = dict(
                        encoding=config["encoding"],
                        sep=config["sep"],
                        on_bad_lines="skip",
                    )
                    if parse_numerico and config["sep"] == ";":
                        kwargs.update(
                            usecols=lambda c: str(c).strip().replace("\ufeff", "").upper()
                            in colunas_uteis,
                            dtype={
                                "REG_ANS": str,
                                "CD_CONTA_CONTABIL": str,
                                "DESCRICAO": str,
                                "DATA": str,
                            },
                            decimal=",",
                            thousands=".",
                        )
                    else:
                        kwargs["dtype"] = str

                    df = pd.read_csv(csv_path, **kwargs)

                    required_cols = ["REG_ANS", "DESCRICAO", "VL_SALDO_FINAL"]
                    cols_upper = [c.upper() for c in df.columns]

                    if all(col in cols_upper for col in required_cols):
                        logger.debug(
                            f"✅ CSV lido com {config['encoding']} + sep '{config['sep']}'"
                        )
                        return df

                except Exception as e:
                    logger.debug(f"⚠️  Falha ao ler com {config}: {e}")
                    continue

            if tentativa == 0:
                logger.warning(f"⚠️  Falha ao ler {csv_path.name}; nova tentativa em 3s...")
                time.sleep(3)

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
        df["CD_CONTA_CONTABIL"] = df["CD_CONTA_CONTABIL"].fillna("").astype(str).str.strip()
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
        df["VL_SALDO_FINAL"] = parse_serie_valor_brl(df["VL_SALDO_FINAL"])

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
                    logger.debug(f"✅ CADOP lido com {config['encoding']} + sep '{config['sep']}'")
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
            logger.error(f"❌ Coluna REG_ANS não encontrada. Colunas: {list(df.columns)}")
            return pd.DataFrame(columns=["REG_ANS", "RAZAO_SOCIAL"])

        df = df.rename(columns=rename_map)

        if "RAZAO_SOCIAL" not in df.columns:
            df["RAZAO_SOCIAL"] = "OPERADORA SEM NOME"

        # Mesma canonicalização do lado das demonstrações: o CADOP pode vir
        # com "5711" e o 4T com "005711" (ou vice-versa).
        df["REG_ANS"] = normalizar_serie_registro_ans(df["REG_ANS"])
        df = df[df["REG_ANS"] != ""]

        # Campos cadastrais completos (base para a tabela ``operadoras``).
        for origem, destino in self.CADOP_CAMPOS.items():
            if origem in df.columns and destino not in df.columns:
                df[destino] = df[origem]
            elif destino not in df.columns:
                df[destino] = ""

        colunas = ["REG_ANS", "RAZAO_SOCIAL"] + [
            c for c in self.CADOP_CAMPOS.values() if c in df.columns
        ]
        df_final = df[colunas].drop_duplicates(subset=["REG_ANS"], keep="first")

        logger.success(f"✅ CADOP carregado: {len(df_final)} operadoras")
        return df_final

    def carregar_cadop(self) -> pd.DataFrame:
        """Cadastro CADOP normalizado (REG_ANS canônico + campos cadastrais)."""
        return self._load_cadop()

    def df_bruto(self, ano: int) -> pd.DataFrame:
        """Frame bruto (deduplicado) do ano — usado pelo gate de qualidade."""
        return self._ler_df_all(ano)

    # ------------------------------------------------------------------
    # MÉTODO D (núcleo puro — reutilizável para qualquer prefixo de conta)
    # ------------------------------------------------------------------
    @staticmethod
    def metodo_d_total(valores: dict) -> float:
        """
        Aplica o MÉTODO D (híbrido) sobre {conta: valor} de UMA operadora.

        Metodologia:
        1. Identifica raízes (contas sem ancestral presente no dicionário)
        2. Para cada raiz:
           - Se tem folhas descendentes que cobrem ≥90% do valor → usa folhas
           - Se folhas > raiz → usa folhas (raiz subdeclarada)
           - Senão → usa raiz (folhas incompletas ou inexistentes)

        Resultado: sem dupla contagem, sem perder sintéticas, sem descartar negativos.
        """
        contas = list(valores.keys())
        contas_set = set(contas)

        raizes = [c for c in contas if not any(c[:L] in contas_set for L in range(1, len(c)))]

        total = 0.0
        for raiz in raizes:
            folhas_desc = [
                c
                for c in contas
                if c != raiz
                and c.startswith(raiz)
                and not any(c[:L] in contas_set for L in range(len(raiz) + 1, len(c)))
            ]

            if not folhas_desc:
                # Raiz sem folhas: usa o próprio valor (±)
                total += valores[raiz]
            else:
                soma_folhas = sum(valores[f] for f in folhas_desc)
                if soma_folhas >= 0.9 * valores[raiz] or soma_folhas > valores[raiz]:
                    # Folhas cobrem bem ou superam a raiz
                    total += soma_folhas
                else:
                    # Folhas incompletas: usa raiz
                    total += valores[raiz]

        return total

    def _metodo_d_por_operadora(self, df_nz: pd.DataFrame) -> dict:
        """Aplica Método D por REG_ANS sobre um df já filtrado (valores ≠ 0)."""
        resultados = {}
        for reg, grupo in df_nz.groupby("REG_ANS"):
            contas = grupo["CD_CONTA_CONTABIL"].tolist()
            valores = dict(zip(contas, grupo["VL_SALDO_FINAL"]))
            resultados[reg] = self.metodo_d_total(valores)
        return resultados

    # ------------------------------------------------------------------
    # LEITURA BRUTA POR ANO (cacheado — evita reler ZIPs por dimensão/F2.4)
    # ------------------------------------------------------------------
    def _ler_df_all(self, ano: int) -> pd.DataFrame:
        """Extrai ZIPs e concatena todos os trimestres de um ano (cacheado)."""
        cached = getattr(self, "_df_all_cache", None)
        if cached is not None and cached[0] == ano:
            return cached[1]

        csv_files = self.extract_zips(ano)
        if not csv_files:
            raise ValueError("Nenhum CSV extraído")

        dfs = []
        linhas_brutas = 0
        for csv_path in csv_files:
            trimestre = csv_path.stem
            logger.info(f"📊 Lendo {trimestre}...")
            df = self._read_csv_demonstracao(csv_path, parse_numerico=True)
            linhas_brutas += len(df)
            df["TRIMESTRE"] = trimestre
            df["CD_CONTA_CONTABIL"] = df["CD_CONTA_CONTABIL"].fillna("").str.strip()

            # P0-3: canonicaliza o REG_ANS já por arquivo (5711 == 005711).
            df["REG_ANS"] = normalizar_serie_registro_ans(df["REG_ANS"])
            # P0-1: converte 1.234,56 antes de qualquer concat.
            df["VL_SALDO_FINAL"] = parse_serie_valor_brl(df["VL_SALDO_FINAL"])

            colunas = ["REG_ANS", "CD_CONTA_CONTABIL", "VL_SALDO_FINAL", "TRIMESTRE"]
            if "DATA" in df.columns:
                colunas.append("DATA")
            df = df[colunas]
            df = df[df["REG_ANS"] != ""]

            # Reduz cada trimestre a UMA linha por conta antes de concatenar.
            # O Método D só precisa do último valor não-zero de cada conta;
            # manter os ~3 milhões de linhas brutas em memória era o que
            # estourava o commit do Windows durante o reload.
            df = df[df["VL_SALDO_FINAL"] != 0]
            df, _ = deduplicar_contas(
                df,
                chaves=("REG_ANS", "CD_CONTA_CONTABIL", "TRIMESTRE"),
                coluna_data="DATA",
            )
            df = df.drop_duplicates(subset=["REG_ANS", "CD_CONTA_CONTABIL"], keep="last").drop(
                columns=["DATA"], errors="ignore"
            )
            dfs.append(df)

        df_all = pd.concat(dfs, ignore_index=True)
        df_all = df_all[df_all["REG_ANS"] != ""]
        df_all, removidas = deduplicar_contas(df_all)
        if removidas:
            logger.info(f"🧹 {removidas:,} linhas duplicadas removidas (mesma conta/trimestre)")

        logger.info(
            f"📊 Linhas brutas: {linhas_brutas:,} | "
            f"contas/trimestre: {len(df_all):,} | "
            f"operadoras: {df_all['REG_ANS'].nunique():,}"
        )

        self._df_all_cache = (ano, df_all)
        return df_all

    # ------------------------------------------------------------------
    # PROCESSAMENTO GENÉRICO POR PREFIXOS (F2.4 — múltiplas dimensões)
    # ------------------------------------------------------------------
    def processar_contas(
        self,
        ano: int,
        prefixos: dict,
        output_col: str = "gasto_total",
        quarterly_output: bool = False,
    ) -> pd.DataFrame:
        """
        Processa MÚLTIPLOS prefixos contábeis em uma única passada do Método D.

        Args:
            ano: ano das demonstrações (ex.: 2024)
            prefixos: {nome_da_coluna: prefixo_de_conta}, ex. {"receita": "31"}.
                O prefixo pode ser uma tupla para somar várias contas na mesma
                coluna (ex.: {"caixa": ("121", "122")}).
            output_col: coluna principal (usada p/ ordenação e fallback)
            quarterly_output: se True, gera também colunas <nome>_<trim> por
                              prefixo (histórico trimestral — F3.2)

        Returns:
            DataFrame com REG_ANS, RAZAO_SOCIAL + uma coluna por prefixo
            (+ colunas trimestrais quando solicitado).
        """
        df_all = self._ler_df_all(ano)
        prefix_list = []
        for valor in prefixos.values():
            if isinstance(valor, str):
                prefix_list.append(valor)
            else:
                prefix_list.extend(list(valor))
        prefix_list = list(dict.fromkeys(prefix_list))
        mask = df_all["CD_CONTA_CONTABIL"].str.startswith(tuple(prefix_list))
        df_ramo = df_all[mask].copy()
        logger.info(f"🌳 Prefixos {prefix_list}: {len(df_ramo):,} registros ({ano})")

        def _aggregate(df_src: pd.DataFrame, suffix: str = "") -> pd.DataFrame:
            frames = []
            for nome, pref in prefixos.items():
                # Uma coluna pode agregar VÁRIOS prefixos (ex.: caixa =
                # 121 Disponível + 122 Aplicações Financeiras). Cada prefixo
                # é consolidado pelo Método D e os resultados são somados.
                prefixos_coluna = [pref] if isinstance(pref, str) else list(pref)
                por_operadora: dict = {}
                for p in prefixos_coluna:
                    sub = df_src[df_src["CD_CONTA_CONTABIL"].str.startswith(p)]
                    nz = sub[sub["VL_SALDO_FINAL"] != 0]
                    res = self._metodo_d_por_operadora(nz)
                    for reg, valor in res.items():
                        por_operadora[reg] = por_operadora.get(reg, 0.0) + valor
                if por_operadora:
                    frames.append(
                        pd.DataFrame(
                            [{"REG_ANS": r, nome + suffix: v} for r, v in por_operadora.items()]
                        )
                    )
            if not frames:
                cols = ["REG_ANS"] + [p + suffix for p in prefixos]
                return pd.DataFrame(columns=cols)
            out = frames[0]
            for f in frames[1:]:
                out = out.merge(f, on="REG_ANS", how="outer")
            return out

        # Consolidação anual: último valor não-zero por (REG_ANS, conta)
        df_last = (
            df_ramo[df_ramo["VL_SALDO_FINAL"] != 0]
            .sort_values("TRIMESTRE")
            .groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False)
            .tail(1)
        )
        consolidated = _aggregate(df_last)
        if output_col not in consolidated.columns:
            consolidated[output_col] = 0.0
        consolidated = consolidated.fillna(0)
        logger.info(f"🌱 Operadoras com valor: {len(consolidated):,}")

        quarter_cols = []
        if quarterly_output:
            for trimestre in sorted(df_all["TRIMESTRE"].unique()):
                df_tri = df_ramo[df_ramo["TRIMESTRE"] == trimestre]
                tri_frame = _aggregate(df_tri, suffix=f"_{trimestre}")
                consolidated = consolidated.merge(tri_frame, on="REG_ANS", how="left")
                quarter_cols += [p + f"_{trimestre}" for p in prefixos]
            consolidated = consolidated.fillna(0)

        # Juntar com CADOP
        logger.info("🔗 Juntando com CADOP...")
        cadop = self._load_cadop()
        consolidated["REG_ANS"] = normalizar_serie_registro_ans(consolidated["REG_ANS"])
        consolidated = consolidated[consolidated["REG_ANS"] != ""].copy()
        consolidated = consolidated.drop_duplicates(subset=["REG_ANS"], keep="last")

        if cadop.empty:
            logger.warning("⚠️  CADOP vazio, usando nome padrão")
            consolidated["RAZAO_SOCIAL"] = "OPERADORA SEM NOME"
        else:
            cadop = cadop.copy()
            cadop["REG_ANS"] = normalizar_serie_registro_ans(cadop["REG_ANS"])
            consolidated = consolidated.merge(cadop, on="REG_ANS", how="left")
            consolidated["RAZAO_SOCIAL"] = consolidated["RAZAO_SOCIAL"].fillna("OPERADORA SEM NOME")

        ordered = ["REG_ANS", "RAZAO_SOCIAL"] + list(prefixos.keys()) + quarter_cols
        # output_col pode não ser um prefixo nomeado (ex.: chamada com apenas
        # {"receita": "31"}); incluí-la garante a coluna criada acima.
        if output_col not in ordered:
            ordered.insert(len(prefixos) + 2, output_col)
        seen = set()
        ordered = [c for c in ordered if not (c in seen or seen.add(c))]
        consolidated = consolidated[[c for c in ordered if c in consolidated.columns]]
        consolidated = consolidated.sort_values(output_col, ascending=False)

        total = consolidated[output_col].sum()
        logger.success(
            f"✅ Consolidação completa: {len(consolidated)} operadoras | "
            f"R$ {total:,.0f} (Método D - híbrido)"
        )
        return consolidated

    # ------------------------------------------------------------------
    # PROCESSAMENTO PRINCIPAL (API pública legado — agora delega)
    # ------------------------------------------------------------------
    def processar_ano(
        self, ano: int = 2024, prefixo: str = "41", quarterly_output: bool = True
    ) -> pd.DataFrame:
        """
        Processa todos os trimestres e consolida usando MÉTODO D (híbrido).

        Retrocompatível: ``processar_ano(2024)`` retorna o mesmo schema de
        antes (REG_ANS, RAZAO_SOCIAL, gasto_<TRIM><ANO>..., gasto_total).

        Genérico (F2.4): ``processar_ano(2024, prefixo="31")`` processa
        qualquer outra dimensão contábil (receita, despesas adm, ativo etc.).
        """
        logger.info(f"🔄 Processando demonstrações contábeis de {ano} (ramo {prefixo})...")
        df = self.processar_contas(
            ano,
            prefixos={"gasto_total": prefixo},
            output_col="gasto_total",
            quarterly_output=quarterly_output,
        )

        if quarterly_output:
            # Compatibilidade histórica: "gasto_total_1T2024" → "gasto_1T2024".
            rename = {
                c: "gasto_" + c[len("gasto_total_") :]
                for c in df.columns
                if c.startswith("gasto_total_")
            }
            df = df.rename(columns=rename)
        return df

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
        print("\n📊 ESTATÍSTICAS")
        print(f"   Total de operadoras: {len(df_consolidated):,}")
        print(f"   Gasto total 2024: R$ {total:,.2f}")
        print(f"   Média por operadora: R$ {df_consolidated['gasto_total'].mean():,.2f}")
        print(f"   Mediana: R$ {df_consolidated['gasto_total'].median():,.2f}")
        print("=" * 80)

    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
