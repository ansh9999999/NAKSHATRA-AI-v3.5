from contextlib import asynccontextmanager

from fastapi import FastAPI

from scheduler import start_scheduler
from logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NAKSHATRA AI v3.5")
    start_scheduler()
    yield
    logger.info("Stopping NAKSHATRA AI v3.5")


app = FastAPI(
    title="NAKSHATRA AI v3.5",
    version="3.5",
    lifespan=lifespan
)


@app.get("/")
def home():
    return {
        "project": "NAKSHATRA AI",
        "version": "3.5",
        "status": "Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
