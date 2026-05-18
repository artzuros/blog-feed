from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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
    action: str  # 'accept', 'reject', 'llm_review'
    
class StatsResponse(BaseModel):
    total_articles: int
    total_blogs: int
    pending_suggestions: int
    accepted_suggestions: int
    articles_by_source: dict
    avg_scores: dict