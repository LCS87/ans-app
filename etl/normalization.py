"""Normalização de identificadores e valores monetários da ANS.

Os arquivos abertos da ANS usam o formato brasileiro nos valores
(``1.234.567,89``) e o ``REG_ANS`` ora com zeros à esquerda, ora sem
(``005711`` vs ``5711``). Este módulo centraliza as duas regras para que
ETL, loader, validação e API usem exatamente a mesma chave e o mesmo
número.

Regras de ``REG_ANS``:
- remove espaços, aspas e caracteres não numéricos;
- remove o sufixo ``.0`` que às vezes aparece quando o CSV é lido como
  numérico;
- completa com zeros à esquerda até 6 dígitos (padrão CADOP/ANS).

Regras de valor:
- se houver vírgula e ponto, o separador mais à direita é o decimal
  (aceita ``1.234,56`` e ``1,234.56``);
- se houver só vírgula, ela é o decimal;
- se houver só ponto e o padrão for de milhar (``1.234`` / ``1.234.567``),
  o ponto é removido;
- caso contrário, o ponto é tratado como decimal (``1234.56``);
- parênteses e sinal negativo são preservados.
"""

from __future__ import annotations

import re
from typing import Union

import pandas as pd

Numero = Union[int, float, str, None]

_REGISTRO_NAO_DIGITO = re.compile(r"\D")
_MILHAR_SEM_VIRGULA = re.compile(r"-?\d{1,3}(?:\.\d{3})+")
_SUFIXO_ZERO = re.compile(r"\.0+$")


def normalizar_registro_ans(valor) -> str:
    """Retorna o ``REG_ANS`` canônico com 6 dígitos.

    >>> normalizar_registro_ans("5711")
    '005711'
    >>> normalizar_registro_ans("005711")
    '005711'
    >>> normalizar_registro_ans(" 5711.0 ")
    '005711'
    >>> normalizar_registro_ans(None)
    ''
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""

    texto = str(valor).strip().strip('"').strip("'")
    if not texto or texto.lower() in {"nan", "none", "<na>", "null"}:
        return ""

    # pandas pode devolver "5711.0" quando a coluna foi inferida como float.
    texto = _SUFIXO_ZERO.sub("", texto)
    digitos = _REGISTRO_NAO_DIGITO.sub("", texto)
    if not digitos:
        return ""

    return digitos.zfill(6)


def normalizar_serie_registro_ans(series: pd.Series) -> pd.Series:
    """Versão vetorizada de :func:`normalizar_registro_ans`."""
    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    texto = series.astype("string").str.strip().str.strip('"').str.strip("'")
    texto = texto.str.replace(r"\.0+$", "", regex=True)
    digitos = texto.str.replace(r"\D", "", regex=True)
    normalizado = digitos.str.zfill(6)
    # zfill("") devolve "000000"; registros vazios devem continuar vazios.
    return normalizado.mask(digitos.isna() | digitos.eq(""), "").fillna("")


def deduplicar_contas(
    df: pd.DataFrame,
    chaves: tuple[str, ...] | None = None,
    coluna_data: str = "DATA",
) -> tuple[pd.DataFrame, int]:
    """Remove duplicatas exatas e mantém a linha mais recente por conta.

    A ANS repete a mesma conta em alguns arquivos (às vezes com a mesma
    data, às vezes com datas de publicação diferentes). Sem isso, o
    ``dict(zip(...))`` do Método D escolhe uma linha arbitrária.

    Returns:
        ``(dataframe_deduplicado, quantidade_removida)``.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df, 0

    chaves = chaves or ("REG_ANS", "CD_CONTA_CONTABIL", "TRIMESTRE")
    chaves_presentes = [c for c in chaves if c in df.columns]
    if not chaves_presentes:
        return df, 0

    antes = len(df)
    out = df.drop_duplicates()

    if coluna_data in out.columns:
        # Datas ISO ordenam lexicograficamente; NaN fica no início para
        # que uma linha datada prevaleça sobre uma linha sem data.
        out = out.sort_values(
            chaves_presentes + [coluna_data],
            kind="mergesort",
            na_position="first",
        )

    out = out.drop_duplicates(subset=chaves_presentes, keep="last")
    return out.reset_index(drop=True), antes - len(out)


def parse_valor_brl(valor: Numero, *, preencher_zero: bool = True) -> float:
    """Converte um valor monetário da ANS para ``float``.

    Valores já numéricos são devolvidos como ``float``. Strings vazias ou
    inválidas retornam ``0.0`` (ou ``nan`` quando ``preencher_zero=False``).
    """
    if valor is None:
        return 0.0 if preencher_zero else float("nan")
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if pd.isna(valor):
            return 0.0 if preencher_zero else float("nan")
        return float(valor)

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none", "<na>", "null", "-"}:
        return 0.0 if preencher_zero else float("nan")

    # (1.234,56) também representa negativo em alguns layouts.
    negativo = texto.startswith("(") and texto.endswith(")")
    if negativo:
        texto = texto[1:-1]

    texto = texto.replace("R$", "").replace("\xa0", "").replace(" ", "").replace("+", "")

    # Alguns layouts colocam o sinal no final (1.234,56-).
    if texto.endswith("-"):
        negativo = True
        texto = texto[:-1]

    if not texto:
        return 0.0 if preencher_zero else float("nan")

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            # Brasileiro: 1.234,56
            texto = texto.replace(".", "").replace(",", ".")
        else:
            # Americano: 1,234.56
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "." in texto and _MILHAR_SEM_VIRGULA.fullmatch(texto):
        # 1.234 ou 1.234.567 (sem parte decimal)
        texto = texto.replace(".", "")

    try:
        numero = float(texto)
    except ValueError:
        return 0.0 if preencher_zero else float("nan")

    return -numero if negativo else numero


def parse_serie_valor_brl(series: pd.Series, *, preencher_zero: bool = True) -> pd.Series:
    """Versão vetorizada de :func:`parse_valor_brl` para o ETL.

    ``preencher_zero=False`` é usado pelo gate de qualidade para contar
    valores realmente inválidos, em vez de escondê-los atrás de zero.
    """
    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    if pd.api.types.is_numeric_dtype(series):
        valores = series.astype(float)
        return valores.fillna(0.0) if preencher_zero else valores

    texto = series.astype("string").str.strip()
    texto = (
        texto.str.replace("R$", "", regex=False)
        .str.replace("\xa0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("+", "", regex=False)
    )

    negativo = texto.str.startswith("(") & texto.str.endswith(")")
    texto = texto.mask(negativo, texto.str.slice(1, -1))
    sinal_final = texto.str.endswith("-")
    texto = texto.mask(sinal_final, texto.str.slice(0, -1))
    sinal_negativo = negativo | sinal_final

    tem_virgula = texto.str.contains(",", regex=False)
    tem_ponto = texto.str.contains(r"\.", regex=True)
    ambos = tem_virgula & tem_ponto

    # O separador decimal é o que aparece mais à direita.
    if ambos.any():
        ultima_virgula = texto.str.rfind(",")
        ultimo_ponto = texto.str.rfind(".")
        brasileiro = ambos & (ultima_virgula > ultimo_ponto)
        americano = ambos & (ultimo_ponto > ultima_virgula)

        texto = texto.mask(
            brasileiro,
            texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        )
        texto = texto.mask(
            americano,
            texto.str.replace(",", "", regex=False),
        )

    so_virgula = tem_virgula & ~tem_ponto
    texto = texto.mask(
        so_virgula,
        texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )

    so_ponto = tem_ponto & ~tem_virgula
    milhar = so_ponto & texto.str.fullmatch(r"-?\d{1,3}(?:\.\d{3})+")
    texto = texto.mask(milhar, texto.str.replace(".", "", regex=False))

    valores = pd.to_numeric(texto, errors="coerce").astype("float64")
    if sinal_negativo.any():
        valores = valores.mask(sinal_negativo, -valores)

    return valores.fillna(0.0) if preencher_zero else valores
