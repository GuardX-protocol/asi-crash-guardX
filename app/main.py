from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import users, crypto, telegram
from app.routers.telegram_webhook import router as telegram_webhook_router
from app.database import connect_to_mongo, close_mongo_connection
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GuardX Crypto Monitor",
    description="Crypto monitoring and crash detection with Telegram integration",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(crypto.router, prefix="/crypto", tags=["crypto-monitoring"])
app.include_router(telegram.router, prefix="/telegram", tags=["telegram-notifications"])
app.include_router(telegram_webhook_router, prefix="/telegram", tags=["telegram-webhook"])

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting GuardX API...")
    
    try:
        mongo_connected = await connect_to_mongo()
        if mongo_connected:
            logger.info("✅ MongoDB connected")
        else:
            logger.warning("⚠️ MongoDB connection failed")
    except Exception as e:
        logger.error(f"❌ MongoDB startup error: {e}")
    
    logger.info("🚀 Startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    await close_mongo_connection()
    logger.info("✅ Shutdown complete")

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "GuardX Crash Sentinel API",
        "version": "2.0.0",
        "platform": "vercel",
        "telegram_bot": "@guardx_detector_bot"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/test")
def test():
    return {"message": "API is working!", "timestamp": datetime.utcnow().isoformat()}

@app.get("/system/status")
async def get_system_status():
    """Get basic system status"""
    from app.database import is_connected
    
    try:
        return {
            "system": {
                "status": "operational",
                "timestamp": datetime.utcnow().isoformat()
            },
            "database": {
                "status": "connected" if is_connected() else "disconnected",
                "mongodb_url_configured": bool(os.getenv("MONGODB_URL"))
            },
            "telegram": {
                "bot_configured": bool(os.getenv('TELEGRAM_BOT_TOKEN')),
                "webhook_endpoint": "/telegram/webhook"
            },
            "environment": {
                "platform": "vercel" if os.getenv("VERCEL") else "local"
            }
        }
    except Exception as e:
        return {
            "system": {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        }

@app.get("/telegram/test")
async def test_telegram():
    """Test Telegram bot configuration"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return {"error": "TELEGRAM_BOT_TOKEN not configured"}
        
        import aiohttp
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "✅ Bot configured correctly",
                        "bot_info": data.get("result", {}),
                        "webhook_url": "https://asi-crash-guard-x.vercel.app/telegram/webhook"
                    }
                else:
                    return {
                        "status": "❌ Bot configuration error",
                        "error": f"HTTP {response.status}"
                    }
    except Exception as e:
        return {
            "status": "❌ Error testing bot",
            "error": str(e)
        }