from fastapi import Security, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from config.settings import API_KEY
from api.logger import api_logger

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_admin_key(api_key: str = Security(api_key_header)):
    """Verify admin API key."""
    api_logger.debug("Admin key verification attempted")
    
    if not api_key:
        api_logger.warning("Admin access denied: No API key provided")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    
    if api_key != API_KEY:
        # Log only first 8 chars for security
        key_preview = api_key[:8] + "..." if len(api_key) > 8 else "***"
        api_logger.warning(f"Admin access denied: Invalid API key (preview: {key_preview})")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    
    api_logger.debug("Admin API key validated successfully")
    return api_key

def optional_key(api_key: str = Security(api_key_header)):
    """Optional API key (for endpoints that can be public or admin)."""
    if api_key:
        api_logger.debug("Optional API key provided")
    return api_key