# ml-proj

ML project: FastAPI service + sklearn pipeline, MongoDB storage.

## Stack
- Python >=3.13, managed with **uv** (`uv add <pkg>`, `uv sync`, `uv run python main.py`)
- FastAPI, uvicorn, pydantic / pydantic-settings
- pandas, numpy, scikit-learn
- pymongo (MongoDB)
- loguru (logging)

## Layout
- `app/components/` — pipeline stages
- `app/pipeline/` — stage orchestration
- `app/entity/` — config/artifact schemas
- `app/constants/` — constants
- `app/exception/` — custom exceptions
- `app/cloud/` — cloud helpers
- `app/utils/` — shared helpers
- `app/logging/logger.py` — logging setup
- `notebooks/` — experiments only, no prod code
- `data/` — datasets, never commit large files

## Logging
- Always `from app.logging.logger import logger`. Never `print()`, never stdlib `logging.basicConfig`.
- Importing the module creates a new file per run: `logs/<YYYY-MM-DD>/<HH-MM-SS>.log`. Every log line includes entry script name as `[script]`.
- Files older than 7 days auto-deleted on startup. `logs/` is gitignored.
- Entry scripts must import the logger first so each run writes a log.
- Use `logger.exception(...)` inside `except` blocks to keep traceback.

## Conventions
- Type hints on all public functions.
- Config via `.env` loaded by pydantic-settings. Copy `.env.example`; never commit `.env` or secrets.
- Raise custom exceptions from `app/exception/`, don't swallow errors.
- Keep functions small; one responsibility per component.

## Commands
- Install: `uv sync`
- Run: `uv run python main.py`
- API: `uv run uvicorn app.main:app --reload` (adjust to actual module)

## Rules
- Add dependencies via `uv add`, keep `pyproject.toml` and `uv.lock` in sync.
- Don't edit `uv.lock` by hand.
- Ask before destructive actions (deleting data, force-push).
