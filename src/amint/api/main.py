"""
Main FastAPI application for A-MINT.
"""
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from .endpoints import transform
import logging
import os

app = FastAPI(
    title="A-MINT API",
    description="API for transforming pricing pages into structured data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transform.router, prefix="/api/v1", tags=["transform"])

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "UP"}

# Health check endpoint
@app.get("/api/v1/health")
def health_check():
    return {"status": "UP"}

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('logs/amint_api.log'),
        logging.StreamHandler()
    ]
)

# Optionally, set uvicorn loggers to use the same file
for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    uvicorn_logger = logging.getLogger(logger_name)
    uvicorn_logger.handlers = []
    uvicorn_logger.propagate = True 