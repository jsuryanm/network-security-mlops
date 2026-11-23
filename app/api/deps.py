import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI

from app.logging.logger import logger
from app.pipeline.batch_pipeline import LABELS  # noqa: F401 (re-exported)
from app.utils.main_utils.utils import load_object
from app.utils.ml_utils.estimator import NetworkModel

FINAL_MODEL_DIR = Path("final_models")


def now() -> datetime:
    return datetime.now(timezone.utc)


def _load_network_model() -> NetworkModel | None:
    model_path = FINAL_MODEL_DIR / "model.pkl"
    preprocessor_path = FINAL_MODEL_DIR / "preprocessor.pkl"
    if not (model_path.exists() and preprocessor_path.exists()):
        return None
    return NetworkModel(preprocessor=load_object(preprocessor_path), model=load_object(model_path))


async def reload_model(app: FastAPI) -> None:
    """Load pickles off the event loop, then swap the model reference."""
    async with app.state.model_lock:
        try:
            app.state.model = await asyncio.to_thread(_load_network_model)
        except Exception:
            logger.exception("Model load failed; keeping previous model")
            return
    if app.state.model is None:
        logger.warning(f"No model found in {FINAL_MODEL_DIR}; /predict returns 503 until trained")
