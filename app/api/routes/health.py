import asyncio

import httpx
from fastapi import APIRouter, Request

# Request gives direct access to server to see HTTP request from client
from app.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


async def _ping_mongo(request: Request) -> bool:
    try:
        await request.app.state.mongo.admin.command("ping")
        return True
    except Exception:
        return False


async def _ping_mlflow(request: Request) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            await client.get(request.app.state.settings.mlflow_uri)
        return True  # any HTTP response means reachable (auth may reject)
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    mongodb, mlflow = await asyncio.gather(_ping_mongo(request), _ping_mlflow(request))
    model_loaded = request.app.state.model is not None
    ok = mongodb and mlflow and model_loaded
    return HealthResponse(
        status="ok" if ok else "degraded",
        model_loaded=model_loaded,
        mongodb=mongodb,
        mlflow=mlflow,
    )
