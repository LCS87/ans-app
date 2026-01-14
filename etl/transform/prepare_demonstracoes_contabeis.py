import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd


RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
INTERIM_DIR = Path(__file__).parent.parent / "data" / "interim"

ZIPS_ROOT = RAW_DIR / "demonstracoes_contabeis"
EXTRACTED_ROOT = RAW_DIR / "demonstracoes_contabeis_extracted"
OUT_CSV = INTERIM_DIR / "demonstracoes_contabeis_consolidado.csv"
OUT_VALIDATION_CSV = INTERIM_DIR / "validacao_demonstracoes_contabeis.csv"


@dataclass(frozen=True)
class Periodo:
    ano: int
    trimestre: int


def _ensure_dirs() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_ROOT.mkdir(parents=True, exist_ok=True)


def _parse_period_from_zip_name(zip_name: str) -> Optional[Periodo]:
    # Exemplos vistos no FTP: 1T2024.zip, 4T2024.zip, 2T2025.zip
    m = re.search(r"([1-4])T(20\d{2})", zip_name.upper())
    if not m:
        return None

    trimestre = int(m.group(1))
    ano = int(m.group(2))
    return Periodo(ano=ano, trimestre=trimestre)


def extract_all_zips() -> list[Tuple[Path, Periodo]]:
    """Descompacta todos os ZIPs encontrados em etl/data/raw/demonstracoes_contabeis/**."""

    _ensure_dirs()

    extracted: list[Tuple[Path, Periodo]] = []

    if not ZIPS_ROOT.exists():
        print(f"Pasta não encontrada: {ZIPS_ROOT}")
        return extracted

    zip_files = sorted(ZIPS_ROOT.glob("**/*.zip"))
    if not zip_files:
        print(f"Nenhum ZIP encontrado em: {ZIPS_ROOT}")
        return extracted

    for z in zip_files:
        periodo = _parse_period_from_zip_name(z.name)
        if not periodo:
            print(f"Ignorando ZIP (não reconheci período no nome): {z.name}")
            continue

        out_dir = EXTRACTED_ROOT / str(periodo.ano) / f"{periodo.trimestre}T"
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"Extraindo {z} -> {out_dir}")
        with zipfile.ZipFile(z, "r") as zf:
            zf.extractall(out_dir)

        extracted.append((out_dir, periodo))

    return extracted


def _try_read_csv(path: Path) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Lê CSV tentando encodings comuns e separador automático.

    Retorna (df, encoding_usado).
    """

    encodings = ["utf-8-sig", "utf-8", "latin1"]

    for enc in encodings:
        try:
            # sep=None + engine=python tenta inferir separador
            df = pd.read_csv(path, sep=None, engine="python", encoding=enc, dtype=str)
            return df, enc
        except Exception:
            continue

    return None, None


def _norm_col(c: str) -> str:
    c = str(c).strip().lower()
    c = re.sub(r"\s+", " ", c)
    c = c.replace("á", "a").replace("à", "a").replace("â", "a").replace("ã", "a")
    c = c.replace("é", "e").replace("ê", "e")
    c = c.replace("í", "i")
    c = c.replace("ó", "o").replace("ô", "o").replace("õ", "o")
    c = c.replace("ú", "u")
    c = re.sub(r"[^a-z0-9 ]", "", c)
    return c


def _pick_col(cols_norm: Dict[str, str], candidates: Iterable[str]) -> Optional[str]:
    """Retorna o nome original da coluna cujo nome normalizado contém algum candidato."""
    for original, norm in cols_norm.items():
        for cand in candidates:
            if cand in norm:
                return original
    return None


def _normalize_demonstracoes_schema(df: pd.DataFrame, periodo: Periodo) -> Optional[pd.DataFrame]:
    """Normaliza para o schema alvo:

    ano, trimestre, reg_ans, cd_conta_contabil, descricao_conta, vl_saldo_inicial, vl_saldo_final

    Como os layouts podem variar, a seleção é heurística por nome de coluna.
    """

    if df is None or df.empty:
        return None

    cols_norm = {c: _norm_col(c) for c in df.columns}

    reg_ans_col = _pick_col(cols_norm, ["registro ans", "reg ans", "registroans", "cod operadora", "codigo operadora", "operadora", "regans"])  # heurístico
    cd_conta_col = _pick_col(cols_norm, ["cd conta", "codigo conta", "conta contabil", "cod conta", "cdconta", "cd_conta"])  # heurístico
    desc_col = _pick_col(cols_norm, ["descricao conta", "descricao", "ds conta", "nome conta", "descricao_conta"])  # heurístico

    saldo_ini_col = _pick_col(cols_norm, ["saldo inicial", "vl saldo inicial", "valor saldo inicial", "vlsaldoinicial"])  # heurístico
    saldo_fim_col = _pick_col(cols_norm, ["saldo final", "vl saldo final", "valor saldo final", "vlsaldofinal"])  # heurístico

    # Se não achar colunas mínimas, não é um arquivo de demonstrações no formato esperado
    if not cd_conta_col or not desc_col:
        return None

    out = pd.DataFrame()
    out["ano"] = str(periodo.ano)
    out["trimestre"] = str(periodo.trimestre)

    out["reg_ans"] = df[reg_ans_col] if reg_ans_col else None
    out["cd_conta_contabil"] = df[cd_conta_col]
    out["descricao_conta"] = df[desc_col]

    out["vl_saldo_inicial"] = df[saldo_ini_col] if saldo_ini_col else None
    out["vl_saldo_final"] = df[saldo_fim_col] if saldo_fim_col else None

    # Limpezas
    for c in ["reg_ans", "cd_conta_contabil", "descricao_conta", "vl_saldo_inicial", "vl_saldo_final"]:
        if c in out.columns:
            out[c] = out[c].astype(str).str.strip()
            out.loc[out[c].isin(["", "nan", "None"]), c] = None

    return out


def _detect_columns_for_audit(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Detecta quais colunas (originais) foram usadas para compor o schema normalizado."""


    cols_norm = {c: _norm_col(c) for c in df.columns}

    reg_ans_col = _pick_col(cols_norm, ["registro ans", "reg ans", "registroans", "cod operadora", "codigo operadora", "operadora", "regans"])
    cd_conta_col = _pick_col(cols_norm, ["cd conta", "codigo conta", "conta contabil", "cod conta", "cdconta", "cd_conta"])
    desc_col = _pick_col(cols_norm, ["descricao conta", "descricao", "ds conta", "nome conta", "descricao_conta"])
    saldo_ini_col = _pick_col(cols_norm, ["saldo inicial", "vl saldo inicial", "valor saldo inicial", "vlsaldoinicial"])
    saldo_fim_col = _pick_col(cols_norm, ["saldo final", "vl saldo final", "valor saldo final", "vlsaldofinal"])

    return {
        "det_reg_ans_col": reg_ans_col,
        "det_cd_conta_contabil_col": cd_conta_col,
        "det_descricao_conta_col": desc_col,
        "det_vl_saldo_inicial_col": saldo_ini_col,
        "det_vl_saldo_final_col": saldo_fim_col,
    }


def consolidate_demonstracoes(extracted: list[Tuple[Path, Periodo]]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Percorre arquivos extraídos e gera um DataFrame consolidado + relatório de validação."""

    dfs: list[pd.DataFrame] = []
    audit_rows: list[dict] = []

    for folder, periodo in extracted:
        csv_files = sorted(folder.glob("**/*.csv"))
        if not csv_files:
            print(f"Nenhum CSV encontrado em {folder}")
            continue

        for csv_path in csv_files:
            df_raw, encoding_used = _try_read_csv(csv_path)
            if df_raw is None:
                print(f"Falha ao ler CSV (encoding/separador): {csv_path}")
                audit_rows.append({
                    "arquivo": str(csv_path),
                    "ano": periodo.ano,
                    "trimestre": periodo.trimestre,
                    "status": "read_error",
                    "encoding": None,
                    "linhas_raw": None,
                    "colunas_raw": None,
                    "linhas_normalizadas": None,
                    "det_reg_ans_col": None,
                    "det_cd_conta_contabil_col": None,
                    "det_descricao_conta_col": None,
                    "det_vl_saldo_inicial_col": None,
                    "det_vl_saldo_final_col": None,
                })
                continue

            detected = _detect_columns_for_audit(df_raw)
            df_norm = _normalize_demonstracoes_schema(df_raw, periodo)
            if df_norm is None:
                # Provavelmente não é o CSV de demonstrativos (pode ser dicionário, etc.)
                audit_rows.append({
                    "arquivo": str(csv_path),
                    "ano": periodo.ano,
                    "trimestre": periodo.trimestre,
                    "status": "skipped_not_matching_schema",
                    "encoding": encoding_used,
                    "linhas_raw": int(df_raw.shape[0]),
                    "colunas_raw": int(df_raw.shape[1]),
                    "linhas_normalizadas": None,
                    **detected,
                })
                continue

            print(f"OK: {csv_path.name} -> {df_norm.shape}")
            dfs.append(df_norm)
            audit_rows.append({
                "arquivo": str(csv_path),
                "ano": periodo.ano,
                "trimestre": periodo.trimestre,
                "status": "ok",
                "encoding": encoding_used,
                "linhas_raw": int(df_raw.shape[0]),
                "colunas_raw": int(df_raw.shape[1]),
                "linhas_normalizadas": int(df_norm.shape[0]),
                **detected,
            })

    if not dfs:
        empty_out = pd.DataFrame(columns=[
            "ano",
            "trimestre",
            "reg_ans",
            "cd_conta_contabil",
            "descricao_conta",
            "vl_saldo_inicial",
            "vl_saldo_final",
        ])
        return empty_out, pd.DataFrame(audit_rows)

    out = pd.concat(dfs, ignore_index=True)

    # Remove duplicidades óbvias
    out = out.drop_duplicates()

    return out, pd.DataFrame(audit_rows)


def main():
    print("=== Preparação Demonstrações Contábeis (descompactar + consolidar) ===\n")

    extracted = extract_all_zips()
    if not extracted:
        print("Nada para processar. Baixe os ZIPs antes.")
        return

    df, audit_df = consolidate_demonstracoes(extracted)
    print(f"\nConsolidado: {df.shape}")

    _ensure_dirs()
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"CSV consolidado gerado em: {OUT_CSV}")

    audit_df.to_csv(OUT_VALIDATION_CSV, index=False, encoding="utf-8-sig")
    print(f"Validação gerada em: {OUT_VALIDATION_CSV}")


if __name__ == "__main__":
    main()
