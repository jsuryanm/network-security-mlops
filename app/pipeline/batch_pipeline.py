from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from app.constants.training_pipeline import TARGET_COLUMN
from app.utils.ml_utils.estimator import NetworkModel

CHUNK_SIZE = 10_000
MAX_WORKERS = 4
LABELS = {0: "phishing", 1: "legitimate"}  # transformation maps Result -1 -> 0


def predict_frame(
    model: NetworkModel,
    frame: pd.DataFrame,
    columns: list[str],
    chunk_size: int = CHUNK_SIZE,
) -> pd.DataFrame:
    """Score a frame in parallel chunks. Returns input rows + prediction, label.

    Raises ValueError on feature mismatch or missing values.
    """
    features = frame.drop(columns=[TARGET_COLUMN], errors="ignore")
    if set(features.columns) != set(columns):
        raise ValueError(f"feature mismatch: {sorted(set(features.columns) ^ set(columns))}")
    if features.isna().any().any():
        raise ValueError("missing values in feature columns")

    features = features[columns].astype(int)
    chunks = [features.iloc[i : i + chunk_size] for i in range(0, len(features), chunk_size)]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        parts = list(pool.map(model.predict, chunks))  # map keeps chunk order

    preds = np.concatenate(parts).astype(int) if parts else np.array([], dtype=int)
    result = features.copy()
    result["prediction"] = preds
    result["label"] = result["prediction"].map(LABELS)
    return result
