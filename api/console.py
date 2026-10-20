"""Ajustes de console para execução multiplataforma.

O console padrão do Windows usa cp1252, que não consegue codificar os
símbolos usados nos logs (✓, ⚠, 🌳...). Sem um ajuste explícito, um
simples ``print("✓ ...")`` levanta ``UnicodeEncodeError`` e derruba a API
na inicialização ou o pipeline no final da execução.

Chamar :func:`configurar_console` no início do processo (é feito em
``api/config.py``, importado por toda a aplicação e pelo ETL).
"""

import sys


def configurar_console() -> None:
    """Força UTF-8 tolerante em stdout/stderr (idempotente)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # pragma: no cover - depende do console
            pass
