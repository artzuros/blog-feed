from api.logger import api_logger

# Import all route modules
from api.routes import search, suggestions, blogs, admin, llm

api_logger.debug("All API routes initialized")

__all__ = ['search', 'suggestions', 'blogs', 'admin', 'llm']