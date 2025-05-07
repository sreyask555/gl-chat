from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config.settings import settings
import logging
import certifi

# Configure logging
logger = logging.getLogger(__name__)

# Database client
db_client = None

async def init_db():
    """Initialize database connection and register models"""
    global db_client
    
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}")
        db_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            tlsCAFile=certifi.where()
        )
        
        # Import models here to avoid circular imports
        from app.models.chat_message import ChatMessage
        
        # Initialize Beanie with the MongoDB database and document models
        await init_beanie(
            database=db_client[settings.MONGODB_DB_NAME],
            document_models=[ChatMessage]
        )
        
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise e

async def close_db_connection():
    """Close database connection when the app shuts down"""
    global db_client
    if db_client:
        logger.info("Closing MongoDB connection")
        db_client.close() 