from fastapi import APIRouter

from app.api.routes import batch, health, predict, predictions, train

api_router = APIRouter()
for module in (health, predict, predictions, batch, train):
    api_router.include_router(module.router)
