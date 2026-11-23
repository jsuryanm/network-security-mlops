import asyncio

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas import PredictionPage
from app.logging.logger import logger

router = APIRouter(tags=["predict"])


@router.get("/predictions", response_model=PredictionPage)
async def list_predictions(
    request: Request,
    limit: int = Query(20, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    coll = request.app.state.predictions

    async def page() -> list[dict]:
        cursor = coll.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    try:
        total, items = await asyncio.gather(coll.count_documents({}), page())
    except Exception:
        logger.exception("Predictions query failed")
        raise HTTPException(503, "Database unavailable")
    return PredictionPage(total=total, items=items)
