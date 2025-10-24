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
        database_name = os.getenv("DATABASE_NAME")
        
        if not mongodb_url:
            logger.warning("MongoDB URL not configured or using localhost. Skipping MongoDB connection.")
            return False
        
        database.client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=5000)
        
        # Test connection
        await database.client.admin.command('ping')
        
        database.database = database.client[database_name]
        
        await init_beanie(
            database=database.database,
            document_models=[User, Monitor, MonitorAlert]
        )
        
        database.connected = True
        logger.info(f"Successfully connected to MongoDB: {database_name}")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to connect to MongoDB: {e}")
        logger.info("Application will run without MongoDB persistence")
        database.connected = False
        return False

async def close_mongo_connection():
    if database.client:
        database.client.close()
        database.connected = False

def get_database():
    return database.database

def is_connected():
    return database.connected