from fastapi import Security, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from config.settings import API_KEY
from api.logger import root_logger

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_admin_key(api_key: str = Security(api_key_header)):
    root_logger.debug(f"Auth attempt - Received: '{api_key}'")
    root_logger.debug(f"Expected key length: {len(API_KEY)} chars")
    
    if not api_key or api_key != API_KEY:
        root_logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    root_logger.debug("API key validated successfully")
    return api_key

def optional_key(api_key: str = Security(api_key_header)):
    return api_key