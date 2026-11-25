# ---------- Stage 1: build the virtual environment ----------
FROM python:3.13-slim AS builder

# uv = fast installer. Copy just the binary, pinned to a version.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /bin/uv

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Copy only the dependency files first. Docker caches this layer,
# so changing app code does not reinstall everything.
COPY pyproject.toml uv.lock ./

# Install runtime dependencies only (no dev, no frontend groups).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups --no-install-project


# ---------- Stage 2: the small runtime image ----------
FROM python:3.13-slim

# libgomp1 = OpenMP library that xgboost and scikit-learn need.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Run as a normal user, not root.
RUN useradd --create-home --uid 1000 app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Take only the finished venv from stage 1 (leaves uv and caches behind).
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# App code last, because it changes most often.
COPY --chown=app:app app ./app
COPY --chown=app:app data_schema ./data_schema

# Folders the app writes to. Compose mounts volumes over these.
RUN mkdir -p final_models Artifacts logs && chown app:app final_models Artifacts logs

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/health', timeout=4)"

# ONE worker: training status is kept in memory.
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
