from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config.settings import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify JWT token and extract user ID
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extract user ID from payload
        user_id = payload.get("userId")
        if user_id is None:
            raise HTTPException(
                status_code=401, 
                detail="Invalid authentication token - userId missing"
            )
            
        # Return the user_id (model methods will handle ObjectId conversion)
        return user_id
    except JWTError as e:
        logger.error(f"JWT verification error: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail="Invalid authentication token"
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail="Authentication error"
        ) 