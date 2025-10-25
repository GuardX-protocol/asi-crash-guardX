from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import users, crypto, telegram
from app.routers.telegram_webhook import router as telegram_webhook_router
from app.database import connect_to_mongo, close_mongo_connection
# Optional import for crash detector agent
try:
    from app.agents.crash_detector import crash_sentinel
    CRASH_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Crash agent not available: {e}")
    crash_sentinel = None
    CRASH_AGENT_AVAILABLE = False
from app.services.telegram_polling import start_telegram_polling, stop_telegram_polling, get_polling_status
# Optional import for monitor service
try:
    from app.services.monitor_service import start_monitor_service, stop_monitor_service, get_monitor_service_status
    MONITOR_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Monitor service not available: {e}")
    start_monitor_service = lambda: None
    stop_monitor_service = lambda: None
    get_monitor_service_status = lambda: {"available": False, "error": "Dependencies not available"}
    MONITOR_SERVICE_AVAILABLE = False
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(crypto.router, prefix="/crypto", tags=["crypto-monitoring"])
app.include_router(telegram.router, prefix="/telegram", tags=["telegram-notifications"])
app.include_router(telegram_webhook_router, prefix="/telegram", tags=["telegram-webhook"])



agent_thread = None

def run_agent():
    try:
        if CRASH_AGENT_AVAILABLE and crash_sentinel:
            logger.info("🤖 Starting Crash Sentinel Agent...")
            crash_sentinel.run()
        else:
            logger.warning("🤖 Crash Sentinel Agent not available")
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
    
    # Start crash detection agent (optional)
    if CRASH_AGENT_AVAILABLE:
        agent_thread = threading.Thread(target=run_agent, daemon=True)
        agent_thread.start()
        logger.info("🤖 Crash Sentinel Agent started in background")
    else:
        logger.info("🤖 Crash Sentinel Agent disabled (dependencies not available)")
    
    # Start Telegram polling service
    await start_telegram_polling()
    
    # Start monitor service (if available)
    if MONITOR_SERVICE_AVAILABLE:
        await start_monitor_service()
        logger.info("🔍 Monitor service started")
    else:
        logger.info("🔍 Monitor service disabled (dependencies not available)")
    
    logger.info("🚀 Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    
    # Stop Telegram polling
    stop_telegram_polling()
    
    # Stop monitor service
    if MONITOR_SERVICE_AVAILABLE:
        stop_monitor_service()
    
    # Close MongoDB connection
    await close_mongo_connection()
    
    logger.info("✅ Shutdown complete")

@app.get("/", summary="Root endpoint")
def root():
    return {
        "status": "online",
        "service": "GuardX Crash Sentinel API",
        "version": "1.0.0",
        "platform": "vercel"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/test")
def test():
    return {"message": "API is working!"}

@app.get("/agent/status")
async def get_agent_status():
    """Get the status of communication with the target agent"""
    if not CRASH_AGENT_AVAILABLE:
        return {
            "agent_available": False,
            "message": "Crash agent not available (missing dependencies)",
            "asi_available": os.getenv('ASI_API_KEY') is not None
        }
    
    try:
        from app.agents.crash_detector import get_pending_requests, get_latest_agent_response
        
        pending_requests = get_pending_requests()
        latest_response = get_latest_agent_response()
        
        return {
            "agent_available": True,
            "agent_address": crash_sentinel.address if crash_sentinel else None,
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
    if not CRASH_AGENT_AVAILABLE:
        return {"message": "Crash agent not available"}
    
    try:
        from app.agents.crash_detector import get_latest_agent_response
        return get_latest_agent_response() or {"message": "No responses received yet"}
    except Exception as e:
        return {"error": str(e)}



@app.get("/agent/info")
async def get_agent_info():
    """Get information about the GuardX agent"""
    return {
        "agent_available": CRASH_AGENT_AVAILABLE,
        "agent_address": crash_sentinel.address if CRASH_AGENT_AVAILABLE and crash_sentinel else None,
        "detection_method": "Prophet + ARIMA + Anomaly Detection",
        "analysis_method": "ASI Model Integration",
        "mode": "Standalone - No external agents needed",
        "asi_available": os.getenv('ASI_API_KEY') is not None,
        "features": [
            "Training-free crash detection",
            "ASI-powered explanations", 
            "User chat support",
            "Real-time monitoring",
            "Telegram integration",
            "Multi-wallet support"
        ]
    }

@app.get("/telegram/polling-status")
async def get_telegram_polling_status():
    """Get Telegram polling service status"""
    return get_polling_status()

@app.get("/telegram/polling-status/detailed")
async def get_detailed_telegram_polling_status():
    """Get detailed Telegram polling service status including webhook info"""
    from app.services.telegram_polling import get_detailed_polling_status
    return await get_detailed_polling_status()

@app.get("/monitor/service-status")
async def get_monitor_service_status_endpoint():
    """Get monitor service status"""
    return get_monitor_service_status()

@app.get("/telegram/user-stats")
async def get_telegram_user_stats():
    """Get Telegram user interaction statistics"""
    from app.database import is_connected
    from app.models import User
    
    try:
        if not is_connected():
            return {"error": "Database not available"}
        
        # Get all users with Telegram IDs
        telegram_users = await User.find(User.telegramId != None).to_list()
        
        # Categorize users
        real_wallet_users = [u for u in telegram_users if not u.walletAddress.startswith('tg_')]
        temp_wallet_users = [u for u in telegram_users if u.walletAddress.startswith('tg_')]
        
        # Get recent interactions (last 24 hours)
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_users = [u for u in telegram_users if u.lastLoginAt and u.lastLoginAt >= yesterday]
        
        # Get users with alerts enabled
        alert_users = [u for u in telegram_users if u.notificationPreferences.get('telegram_alerts', False)]
        
        stats = {
            "total_telegram_users": len(telegram_users),
            "real_wallet_users": len(real_wallet_users),
            "temp_wallet_users": len(temp_wallet_users),
            "recent_interactions_24h": len(recent_users),
            "users_with_alerts_enabled": len(alert_users),
            "conversion_rate": round((len(real_wallet_users) / len(telegram_users) * 100), 2) if telegram_users else 0,
            "sample_users": [
                {
                    "telegramId": u.telegramId,
                    "username": u.username,
                    "firstName": u.firstName,
                    "walletType": "real" if not u.walletAddress.startswith('tg_') else "temporary",
                    "alertsEnabled": u.notificationPreferences.get('telegram_alerts', False),
                    "lastInteraction": u.lastLoginAt.isoformat() if u.lastLoginAt else None
                } for u in telegram_users[:5]
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return stats
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/database/status")
async def get_database_status():
    """Get database connection status and test data retrieval"""
    from app.database import is_connected, get_database
    
    try:
        status = {
            "mongodb_connected": is_connected(),
            "mongodb_url_configured": bool(os.getenv("MONGODB_URL")),
            "database_name": os.getenv("DATABASE_NAME", "guardx_monitor"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Test data retrieval
        if is_connected():
            try:
                from app.models import User, Monitor, MonitorAlert
                
                # Count documents
                user_count = await User.count()
                monitor_count = await Monitor.count()
                alert_count = await MonitorAlert.count()
                
                # Get sample data
                sample_users = await User.find_all().limit(3).to_list()
                sample_monitors = await Monitor.find_all().limit(3).to_list()
                
                status.update({
                    "mongodb_data": {
                        "user_count": user_count,
                        "monitor_count": monitor_count,
                        "alert_count": alert_count,
                        "sample_users": [
                            {
                                "walletAddress": user.walletAddress,
                                "telegramId": getattr(user, 'telegramId', None),
                                "username": getattr(user, 'username', None),
                                "createdAt": getattr(user, 'createdAt', None)
                            } for user in sample_users
                        ],
                        "sample_monitors": [
                            {
                                "name": monitor.name,
                                "userId": monitor.userId,
                                "symbols": monitor.symbols,
                                "enabled": monitor.enabled
                            } for monitor in sample_monitors
                        ]
                    }
                })
                
            except Exception as e:
                status["mongodb_error"] = str(e)
        else:
            status["error"] = "Database not connected - fallback storage removed"
        
        return status
        
    except Exception as e:
        return {
            "error": str(e),
            "mongodb_connected": False,
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/database/test-connection")
async def test_database_connection():
    """Test database connection and operations"""
    from app.database import is_connected
    from app.models import User
    
    results = {
        "mongodb_url": os.getenv("MONGODB_URL", "Not configured"),
        "database_name": os.getenv("DATABASE_NAME", "guardx_monitor"),
        "connection_test": None,
        "data_test": None,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Test MongoDB connection
        if is_connected():
            results["connection_test"] = "MongoDB connected"
            
            # Test data operations
            try:
                # Try to find a user
                test_user = await User.find_one()
                if test_user:
                    results["data_test"] = {
                        "status": "Data found",
                        "sample_user": {
                            "walletAddress": test_user.walletAddress,
                            "telegramId": getattr(test_user, 'telegramId', None),
                            "hasData": True
                        }
                    }
                else:
                    results["data_test"] = {
                        "status": "No data found",
                        "message": "Database connected but no users exist"
                    }
                    
            except Exception as e:
                results["data_test"] = {
                    "status": "Data operation failed",
                    "error": str(e)
                }
        else:
            results["connection_test"] = "MongoDB not connected"
            results["data_test"] = {
                "status": "Database unavailable",
                "message": "Fallback storage has been removed - MongoDB required"
            }
        
        return results
        
    except Exception as e:
        results["error"] = str(e)
        return results

