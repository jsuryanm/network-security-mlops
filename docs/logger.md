# Using the logger

Source: `app/logging/logger.py` (built on [loguru](https://github.com/Delgan/loguru)).

## Quick start

```python
from app.logging.logger import logger

logger.info("Pipeline started")
```

That is all. No setup call needed. Importing the module:

1. Creates `logs/<YYYY-MM-DD>/<HH-MM-SS>.log` for this run.
2. Deletes `.log` files older than 7 days (and empty date folders).
3. Attaches two outputs: console (INFO+) and file (DEBUG+).

Run a script 3 times, get 3 log files. Same import in 10 modules, still one file per run (Python caches the module).

## Rules

- Import from `app.logging.logger`, not `loguru` directly. Direct import skips the file setup.
- Run scripts from the project root so `app` is importable: `uv run python main.py` or `uv run python -m app.pipeline.xyz`.
- Entry script must import the logger (directly or via any module that does) or no file is written.

## Log levels

```python
logger.debug("Row count: 1200")        # file only
logger.info("Data loaded")             # console + file
logger.warning("Missing values found") # console + file
logger.error("Validation failed")      # console + file
logger.critical("DB unreachable")      # console + file
```

## Formatting values

Use `{}` placeholders. Lazy, no f-string needed:

```python
logger.info("Loaded {} rows from {}", len(df), path)
logger.info("Train size={size}", size=len(train))
```

## Logging exceptions

Inside `except`, use `logger.exception`. It logs at ERROR and includes the full traceback:

```python
try:
    df = pd.read_csv(path)
except Exception:
    logger.exception("Failed to read {}", path)
    raise
```

Or auto-catch with a decorator:

```python
@logger.catch
def train():
    ...
```

## Example: a pipeline component

`app/components/data_ingestion.py`

```python
import pandas as pd

from app.logging.logger import logger


class DataIngestion:
    def run(self, path: str) -> pd.DataFrame:
        logger.info("Ingestion started: {}", path)
        try:
            df = pd.read_csv(path)
        except Exception:
            logger.exception("Ingestion failed: {}", path)
            raise
        logger.info("Ingestion done: {} rows, {} cols", *df.shape)
        return df
```

## Example: entry script

`main.py`

```python
from app.logging.logger import logger, LOG_FILE_PATH


def main():
    logger.info("App started, log file: {}", LOG_FILE_PATH)


if __name__ == "__main__":
    main()
```

## Example: FastAPI

```python
from fastapi import FastAPI

from app.logging.logger import logger

app = FastAPI()


@app.get("/health")
def health():
    logger.info("Health check")
    return {"status": "ok"}
```

## Context per module (optional)

Tag records with extra fields using `bind`:

```python
log = logger.bind(component="data_ingestion")
log.info("started")
```

## Changing behaviour

All settings live at the top of `app/logging/logger.py`:

| Setting | Default | Meaning |
|---|---|---|
| `RETENTION_DAYS` | `7` | Delete logs older than this |
| `LOG_DIR` | `<project>/logs` | Output folder |
| `LOG_FORMAT` | timestamp, level, module:function:line, message | Line layout |
| console level | `INFO` | in `_setup()` |
| file level | `DEBUG` | in `_setup()` |

## Notes

- `logs/` is gitignored.
- File sink uses `enqueue=True`: safe across threads and multiprocessing.
- `diagnose=False`: tracebacks do not print variable values, so secrets do not leak into logs.
