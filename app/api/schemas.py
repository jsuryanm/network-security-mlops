from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    records: list[dict[str, int]] = Field(min_length=1, max_length=1000)


class Prediction(BaseModel):
    prediction: int
    label: Literal["legitimate", "phishing"]


class PredictResponse(BaseModel):
    predictions: list[Prediction]


class PredictionPage(BaseModel):
    total: int
    items: list[dict]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model_loaded: bool
    mongodb: bool
    mlflow: bool


class TrainingStatus(BaseModel):
    status: Literal["idle", "running", "succeeded", "failed"] = "idle"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    test_f1_score: float | None = None
