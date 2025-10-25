import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models import User, Monitor, MonitorAlert

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None
    connected = False

database = Database()

async def connect_to_mongo():
    try:
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME", "guardx_monitor")
        
        if not mongodb_url:
            logger.error("❌ MONGODB_URL environment variable is required")
            database.connected = False
            return False
        
        if not database_name:
            logger.error("❌ DATABASE_NAME environment variable is required")
            database.connected = False
            return False
        
        logger.info(f"🔗 Connecting to MongoDB: {database_name}")
        logger.info(f"🔗 MongoDB URL configured: {mongodb_url[:50]}...")
        
        # Optimized settings for serverless environments
        database.client = AsyncIOMotorClient(
            mongodb_url, 
            serverSelectionTimeoutMS=15000,  # 15 seconds for faster startup
            connectTimeoutMS=15000,          # 15 seconds
            socketTimeoutMS=15000,           # 15 seconds
            retryWrites=True,
            retryReads=True,
            maxPoolSize=5,                   # Smaller pool for serverless
            minPoolSize=0,                   # No minimum connections
            maxIdleTimeMS=30000,             # Close idle connections faster
            heartbeatFrequencyMS=10000       # Check connection health more frequently
        )
        
        # Test connection with detailed error logging
        logger.info("🔄 Testing MongoDB connection...")
        try:
            await database.client.admin.command('ping')
            logger.info("✅ MongoDB ping successful")
        except Exception as ping_error:
            logger.error(f"❌ MongoDB ping failed: {ping_error}")
            logger.error(f"❌ Error type: {type(ping_error).__name__}")
            database.connected = False
            return False
        
        database.database = database.client[database_name]
        
        # Initialize Beanie with error handling
        try:
            await init_beanie(
                database=database.database,
                document_models=[User, Monitor, MonitorAlert]
            )
            logger.info("✅ Beanie initialized successfully")
        except Exception as beanie_error:
            logger.error(f"❌ Beanie initialization failed: {beanie_error}")
            database.connected = False
            return False
        
        database.connected = True
        logger.info(f"✅ Successfully connected to MongoDB: {database_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        database.connected = False
        return False

async def close_mongo_connection():
    try:
        if database.client:
            database.client.close()
            logger.info("✅ MongoDB connection closed")
        database.connected = False
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")
        database.connected = False

def get_database():
    return database.database

def is_connected():
    return database.connected

async def ensure_connection():
    """Ensure database connection is active, reconnect if needed"""
    if not database.connected:
        logger.info("🔄 Database not connected, attempting to reconnect...")
        return await connect_to_mongo()
    
    # Test if connection is still alive
    try:
        if database.client:
            await database.client.admin.command('ping')
            return True
    except Exception as e:
        logger.warning(f"⚠️ Database connection test failed: {e}")
        database.connected = False
        return await connect_to_mongo()
    
    return True