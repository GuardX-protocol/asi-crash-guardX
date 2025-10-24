from fastapi import FastAPI
from app.routers import users, crypto, telegram
from app.routers.telegram_webhook import router as telegram_webhook_router
from app.database import connect_to_mongo, close_mongo_connection
from app.agents.crash_detector import crash_sentinel
from app.services.telegram_polling import start_telegram_polling, stop_telegram_polling, get_polling_status
from app.services.monitor_service import start_monitor_service, stop_monitor_service, get_monitor_service_status
import asyncio
import logging
import threading
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Crypto Market Monitor & Crash Detector",
    description="A comprehensive FastAPI application with crypto monitoring, crash detection, and uAgents integration",
    version="2.0.0"
)

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(crypto.router, prefix="/crypto", tags=["crypto-monitoring"])
app.include_router(telegram.router, prefix="/telegram", tags=["telegram-notifications"])
app.include_router(telegram_webhook_router, prefix="/telegram", tags=["telegram-webhook"])



agent_thread = None

def run_agent():
    try:
        logger.info("🤖 Starting Crash Sentinel Agent...")
        crash_sentinel.run()
    except Exception as e:
        logger.error(f"Agent error: {e}")

@app.on_event("startup")
async def startup_event():
    global agent_thread
    logger.info("Starting Crypto Market Monitor & Crash Detector...")
    
    # Connect to MongoDB
    mongo_connected = await connect_to_mongo()
    if mongo_connected:
        logger.info("✅ MongoDB connected - Full persistence enabled")
    else:
        logger.info("⚠️  Running without MongoDB - In-memory mode")
    
    # Start crash detection agent
    agent_thread = threading.Thread(target=run_agent, daemon=True)
    agent_thread.start()
    logger.info("🤖 Crash Sentinel Agent started in background")
    
    # Start Telegram polling service
    await start_telegram_polling()
    
    # Start monitor service
    await start_monitor_service()
    
    logger.info("🚀 Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    
    # Stop Telegram polling
    stop_telegram_polling()
    
    # Stop monitor service
    stop_monitor_service()
    
    # Close MongoDB connection
    await close_mongo_connection()
    
    logger.info("✅ Shutdown complete")

@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}



@app.get("/agent/status")
async def get_agent_status():
    """Get the status of communication with the target agent"""
    from app.agents.crash_detector import get_pending_requests, get_latest_agent_response
    
    try:
        pending_requests = get_pending_requests()
        latest_response = get_latest_agent_response()
        
        return {
            "agent_address": crash_sentinel.address,
            "pending_requests_count": len(pending_requests),
            "pending_requests": pending_requests,
            "latest_response": latest_response,
            "asi_available": os.getenv('ASI_API_KEY') is not None
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/agent/latest-response")
async def get_latest_agent_response_endpoint():
    """Get the latest response from the target agent"""
    from app.agents.crash_detector import get_latest_agent_response
    
    try:
        return get_latest_agent_response() or {"message": "No responses received yet"}
    except Exception as e:
        return {"error": str(e)}



@app.get("/agent/info")
async def get_agent_info():
    """Get information about the GuardX agent"""
    return {
        "agent_address": crash_sentinel.address,
        "detection_method": "Prophet + ARIMA + Anomaly Detection",
        "analysis_method": "ASI Model Integration",
        "mode": "Standalone - No external agents needed",
        "asi_available": os.getenv('ASI_API_KEY') is not None,
        "features": [
            "Training-free crash detection",
            "ASI-powered explanations", 
            "User chat support",
            "Real-time monitoring"
        ]
    }

@app.get("/telegram/polling-status")
async def get_telegram_polling_status():
    """Get Telegram polling service status"""
    return get_polling_status()

@app.get("/monitor/service-status")
async def get_monitor_service_status_endpoint():
    """Get monitor service status"""
    return get_monitor_service_status()

