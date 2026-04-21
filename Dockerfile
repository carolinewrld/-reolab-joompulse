ARG PYTHON_VERSION=3.12

# ── Stage 1: deps ──────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.5.4

WORKDIR /app
COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r <(uv pip compile pyproject.toml --quiet)

# ── Stage 2: runtime ───────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -ms /bin/bash joompulse

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

WORKDIR /app
COPY --chown=joompulse:joompulse . /app

USER joompulse

EXPOSE 8000

CMD ["uvicorn", "joompulse.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
