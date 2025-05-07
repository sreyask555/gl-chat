from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat, chat_conversations
from app.config.settings import settings
from app.models import init_db, close_db_connection
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Chat Assistant Service",
    description="Backend service for the chat assistant",
    version="1.0.0"
)

# Add these origins to ensure we can receive requests from the extension
origins = [
    "chrome-extension://*/",  # For Chrome extension in production
    "http://localhost:3000",  # For development server
    "http://localhost:3001",  # For development server
    "chrome-extension://*/",  # For Chrome extension
    "moz-extension://*/", 
    "https://app.heygoodlife.dev",
    "https://app.heygoodlife.dev/*",
    "https://api-gl-backend-beta.onrender.com",
    "https://api-gl-backend-beta.onrender.com/*",
    "*",
]

# Configure CORS with extended settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Authorization"],
)

# Database connection events
@app.on_event("startup")
async def startup_db_client():
    logger.info("Starting up database connection")
    await init_db()

@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("Shutting down database connection")
    await close_db_connection()

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(chat_conversations.router, prefix="/api/chat", tags=["chat history"])

@app.get("/")
async def root():
    return {"message": "Chat Assistant Service is running"} 