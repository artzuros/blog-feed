from fastapi import Security, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from config.settings import API_KEY
import logging

logger = logging.getLogger("blog-scout")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_admin_key(api_key: str = Security(api_key_header)):
    # # Debug prints
    # print(f"=== DEBUG AUTH ===")
    # print(f"Received API Key: '{api_key}'")
    # print(f"Expected API Key: '{API_KEY}'")
    # print(f"Keys match: {api_key == API_KEY}")
    # print(f"API_KEY type: {type(API_KEY)}")
    # print(f"Received type: {type(api_key)}")
    
    # logger.info(f"Auth attempt - Received: '{api_key}', Expected: '{API_KEY}'")
    
    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key

def optional_key(api_key: str = Security(api_key_header)):
    return api_key