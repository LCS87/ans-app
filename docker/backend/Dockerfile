# ---------------------------------------------------------------------------
# ANS Intelligence — Dockerfile multi-stage (Fase 5.2)
# Meta: imagem de produção < 500MB com runtime API + ETL completo.
# Build context esperado: raiz do repositório (ver docker/docker-compose.yml).
#   docker build -f docker/backend/Dockerfile .
# ---------------------------------------------------------------------------

# =========================== STAGE 1: builder ==============================
FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# Toolchain para compilar wheels (hiredis etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.prod.txt ./requirements.txt
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt


# ========================= STAGE 2: production =============================
FROM python:3.12-slim-bookworm AS production

# curl = healthcheck; libgl/libglib/libgomp = runtime do matplotlib.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r ans && useradd -r -g ans -d /app -s /sbin/nologin ans

# Venv compilada no builder (sem pip cache, sem toolchain)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app

# Código-fonte da aplicação (agora inclui db/ e scripts/, que faltavam)
COPY api/ ./api/
COPY etl/ ./etl/
COPY db/ ./db/
COPY scripts/ ./scripts/
COPY requirements.prod.txt ./

# Diretórios de dados do ETL + uploads CSV (permissões ao usuário não-root)
RUN mkdir -p /app/data/raw /app/data/processed /app/data/relatorios /app/uploads \
    && chown -R ans:ans /app

USER ans

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]


# ===================== STAGE 3: testes (não entra na prod) =================
FROM production AS test

USER root
RUN /opt/venv/bin/pip install --no-cache-dir pytest pytest-cov fakeredis
COPY tests/ ./tests/
COPY pytest.ini ./
# Rodar com: docker build --target test -f docker/backend/Dockerfile .
CMD ["/opt/venv/bin/python", "-m", "pytest", "tests/", "-q", "--no-cov"]
