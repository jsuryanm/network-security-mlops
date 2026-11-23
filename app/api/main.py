import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pymongo import AsyncMongoClient

from app.api.deps import reload_model
from app.api.routes import api_router
from app.api.schemas import TrainingStatus
from app.constants.training_pipeline import DATA_INGESTION_DATABASE_NAME, TARGET_COLUMN
from app.core.config import get_settings
from app.logging.logger import logger
from app.utils.main_utils.utils import read_yaml_file

SCHEMA_PATH = Path("data_schema/schema.yaml")
PREDICTIONS_COLLECTION = "predictions"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.mongo = AsyncMongoClient(settings.mongodb_uri)
    app.state.predictions = app.state.mongo[DATA_INGESTION_DATABASE_NAME][PREDICTIONS_COLLECTION]

    schema = await asyncio.to_thread(read_yaml_file, SCHEMA_PATH)
    app.state.feature_columns = [
        name for item in schema["columns"] for name in item if name != TARGET_COLUMN
    ]

    app.state.model = None
    app.state.model_lock = asyncio.Lock()
    app.state.training = TrainingStatus()

    await reload_model(app)
    logger.info("API started")
    try:
        yield
    finally:
        await app.state.mongo.close()
        logger.info("API stopped")


app = FastAPI(title="Phishing Detector API", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)
