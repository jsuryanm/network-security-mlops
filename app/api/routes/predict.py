import asyncio

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, Request

from app.api.deps import LABELS, now
from app.api.schemas import Prediction, PredictRequest, PredictResponse
from app.logging.logger import logger
from app.utils.ml_utils.estimator import NetworkModel

router = APIRouter(tags=["predict"])


async def _log_predictions(app: FastAPI, records: list[dict], preds: list[int]) -> None:
    created_at = now()
    docs = [
        {"features": r, "prediction": p, "created_at": created_at}
        for r, p in zip(records, preds)
    ]
    try:
        await app.state.predictions.insert_many(docs)
    except Exception:
        logger.exception("Failed to log predictions to MongoDB")


@router.post("/predict", response_model=PredictResponse)
async def predict(body: PredictRequest, request: Request, background: BackgroundTasks):
    model: NetworkModel | None = request.app.state.model
    if model is None:
        raise HTTPException(503, "Model not loaded. Train first via POST /train.")

    columns: list[str] = request.app.state.feature_columns
    expected = set(columns)
    for i, record in enumerate(body.records):
        if set(record) != expected:
            diff = sorted(set(record) ^ expected)
            raise HTTPException(422, f"records[{i}] feature mismatch: {diff}")

    frame = pd.DataFrame(body.records)[columns]
    preds = [int(p) for p in await asyncio.to_thread(model.predict, frame)]

    background.add_task(_log_predictions, request.app, body.records, preds)  # don't block response
    return PredictResponse(predictions=[Prediction(prediction=p, label=LABELS[p]) for p in preds])
