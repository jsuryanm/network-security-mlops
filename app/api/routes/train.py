import asyncio

from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, Request

from app.api.deps import now, reload_model
from app.api.schemas import TrainingStatus
from app.logging.logger import logger

router = APIRouter(tags=["train"])


def _train_blocking():
    # Lazy import: model_trainer calls dagshub.init() at import time (network).
    from app.pipeline.training_pipeline import TrainingPipeline

    return TrainingPipeline().run_pipeline()


async def _run_training(app: FastAPI) -> None:
    status: TrainingStatus = app.state.training
    try:
        artifact = await asyncio.to_thread(_train_blocking)
        await reload_model(app)
        status.test_f1_score = artifact.test_metric_artifact.f1_score
        status.status = "succeeded"
    except Exception as e:
        logger.exception("Training failed")
        status.status = "failed"
        status.error = str(e)
    finally:
        status.finished_at = now()


@router.post("/train", response_model=TrainingStatus, status_code=202)
async def train(request: Request, background: BackgroundTasks):
    if request.app.state.training.status == "running":
        raise HTTPException(409, "Training already running")
    request.app.state.training = status = TrainingStatus(status="running", started_at=now())
    background.add_task(_run_training, request.app)
    return status


@router.get("/train/status", response_model=TrainingStatus)
async def train_status(request: Request):
    return request.app.state.training
