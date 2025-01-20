from fastapi import FastAPI
from app.api.endpoints import products
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to SavAI-Backend!"}

app.include_router(products.router, prefix="/api")
