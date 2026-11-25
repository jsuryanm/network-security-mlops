# Build from the repo root:  docker build -f frontend/Dockerfile -t netsec-frontend .

# ---------- Stage 1: install only the frontend dependencies ----------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /bin/uv

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
COPY pyproject.toml uv.lock ./

# --only-group frontend = streamlit, httpx, pandas, pyyaml (no ML libraries).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups --only-group frontend


# ---------- Stage 2: runtime ----------
FROM python:3.13-slim

RUN useradd --create-home --uid 1000 app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_URL=http://backend:8000

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# The UI reads the column names from schema.yaml (../data_schema from frontend/).
COPY --chown=app:app frontend ./frontend
COPY --chown=app:app data_schema/schema.yaml ./data_schema/schema.yaml

USER app
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8501/_stcore/health', timeout=4)"

CMD ["streamlit", "run", "frontend/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", \
     "--browser.gatherUsageStats=false"]