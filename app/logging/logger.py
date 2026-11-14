"""Loguru setup. Import `logger` anywhere; each process run writes a new file.

Layout: logs/<YYYY-MM-DD>/<HH-MM-SS>.log
Files older than RETENTION_DAYS are deleted on startup.
"""
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "logs"
RETENTION_DAYS = 7

LOG_FORMAT = (
    "[ {time:YYYY-MM-DD HH:mm:ss.SSS} ] {level: <8} "
    "{name}:{function}:{line} - {message}"
)


def _cleanup_old_logs(log_dir: Path = LOG_DIR, days: int = RETENTION_DAYS) -> None:
    """Delete *.log older than `days`, then remove emptied date folders."""
    if not log_dir.exists():
        return
    cutoff = time.time() - days * 86400
    for file in log_dir.rglob("*.log"):
        try:
            if file.stat().st_mtime < cutoff:
                file.unlink()
        except OSError:
            pass
    for folder in sorted(log_dir.glob("*/"), reverse=True):
        if folder.is_dir() and not any(folder.iterdir()):
            shutil.rmtree(folder, ignore_errors=True)


def _setup() -> Path:
    now = datetime.now()
    log_file = LOG_DIR / now.strftime("%Y-%m-%d") / f"{now.strftime('%H-%M-%S')}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    _cleanup_old_logs()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format=LOG_FORMAT)
    logger.add(
        log_file,
        level="DEBUG",
        format=LOG_FORMAT,
        encoding="utf-8",
        enqueue=True,  # thread/process safe
        backtrace=True,
        diagnose=False,  # avoid leaking variable values
    )
    return log_file


LOG_FILE_PATH = _setup()

__all__ = ["logger", "LOG_FILE_PATH"]
