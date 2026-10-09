"""Notificações operacionais do pipeline ETL (Fase 5 — observabilidade).

Canais suportados: log estruturado (sempre) e webhook genérico via variável
de ambiente ``ETL_WEBHOOK_URL`` (ex.: Slack/Discord/Teams compatible JSON).
Sem configuração de webhook, a notificação é apenas registrada no log.
"""

from __future__ import annotations

import os

from loguru import logger


def notify_admin(mensagem: str, nivel: str = "info") -> bool:
    """Envia uma notificação ao administrador do pipeline.

    Args:
        mensagem: texto livre da notificação.
        nivel: ``info`` | ``warning`` | ``error``.

    Returns:
        True se algum canal externo entregou; False se apenas log local.
    """
    getattr(logger, nivel if nivel in ("info", "warning", "error") else "info")(
        f"[notify_admin] {mensagem}"
    )

    url = os.getenv("ETL_WEBHOOK_URL", "").strip()
    if not url:
        return False

    try:
        import httpx

        httpx.post(url, json={"text": f"[{nivel.upper()}] {mensagem}"}, timeout=10)
        return True
    except Exception as exc:  # nunca derruba o pipeline por causa de notificação
        logger.warning(f"Falha ao enviar webhook de notificação: {exc}")
        return False
