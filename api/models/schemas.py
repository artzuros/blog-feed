from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from api.logger import api_logger

# Article schemas
class ArticleBase(BaseModel):
    url: str
    title: str
    blog_name: str
    score: float
    llm_score: Optional[float] = None
    combined_score: float
    reason: Optional[str] = None
    keywords: Optional[str] = None
    source: str = 'rss'
    added_by: str = 'automated'
    
    @validator('score', 'combined_score')
    def validate_score(cls, v):
        if v < 0 or v > 1:
            api_logger.warning(f"Invalid score value: {v}")
            raise ValueError('Score must be between 0 and 1')
        return v

class ArticleResponse(ArticleBase):
    fetched_at: datetime

class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[ArticleResponse]

# Blog schemas
class BlogBase(BaseModel):
    name: str
    url: str
    rss: Optional[str] = None
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            api_logger.warning(f"Invalid URL format: {v}")
            raise ValueError('URL must start with http:// or https://')
        return v

class BlogResponse(BlogBase):
    pass

class BlogCreate(BlogBase):
    pass

# Suggestion schemas
class SuggestionBase(BaseModel):
    url: str
    domain: str
    title: str
    subreddit: str
    reddit_score: int
    heuristic_score: float
    llm_score: Optional[float] = None
    combined_score: Optional[float] = None
    reviewed: str = 'pending'
    accepted: bool = False

class SuggestionResponse(SuggestionBase):
    discovered_at: datetime
    reviewed_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None

class SuggestionReview(BaseModel):
    action: str  # 'upvote', 'downvote'
    
    @validator('action')
    def validate_action(cls, v):
        if v not in ['upvote', 'downvote']:
            api_logger.warning(f"Invalid vote action: {v}")
            raise ValueError('Action must be upvote or downvote')
        return v

class StatsResponse(BaseModel):
    total_articles: int
    total_blogs: int
    pending_suggestions: int
    accepted_suggestions: int
    articles_by_source: dict
    avg_scores: dict

api_logger.debug("Pydantic schemas initialized")