import asyncio
import io

import pandas as pd
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.pipeline.batch_pipeline import predict_frame

router = APIRouter(tags=["batch"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("/batch/predict")
async def batch_predict(file: UploadFile, request: Request):
    model = request.app.state.model
    if model is None:
        raise HTTPException(503, "Model not loaded. Train first via POST /train.")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Upload a .csv file")

    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")

    try:
        frame = await asyncio.to_thread(pd.read_csv, io.BytesIO(raw))
        result = await asyncio.to_thread(
            predict_frame, model, frame, request.app.state.feature_columns
        )
    except (ValueError, pd.errors.ParserError) as e:  # EmptyDataError is a ValueError
        raise HTTPException(422, str(e))

    csv_text = await asyncio.to_thread(result.to_csv, index=False)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="predictions.csv"'},
    )
