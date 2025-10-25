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
            raise Exception("MongoDB URL not configured - this is required for the application to function")
        
        if not database_name:
            logger.error("❌ DATABASE_NAME environment variable is required")
            raise Exception("Database name not configured")
        
        logger.info(f"🔗 Connecting to MongoDB: {database_name}")
        database.client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=10000)
        
        # Test connection
        await database.client.admin.command('ping')
        logger.info("✅ MongoDB ping successful")
        
        database.database = database.client[database_name]
        
        await init_beanie(
            database=database.database,
            document_models=[User, Monitor, MonitorAlert]
        )
        
        database.connected = True
        logger.info(f"✅ Successfully connected to MongoDB: {database_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        logger.error("❌ Application cannot start without MongoDB connection")
        database.connected = False
        raise e  # Re-raise the exception to stop the application

async def close_mongo_connection():
    if database.client:
        database.client.close()
        database.connected = False

def get_database():
    return database.database

def is_connected():
    return database.connected