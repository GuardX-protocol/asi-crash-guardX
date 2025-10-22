from fastapi import FastAPI
from app.routers import market, crypto
from app.services.crypto_monitor import crypto_monitor
import asyncio

app = FastAPI(
    title="Crypto Market Monitor & Crash Detector",
    description="A comprehensive FastAPI application with crypto monitoring, crash detection, and uAgents integration",
    version="2.0.0"
)

app.include_router(market.router, prefix="/market", tags=["market-crash-detection"])
app.include_router(crypto.router, prefix="/crypto", tags=["crypto-monitoring"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await crypto_monitor.close()

@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}