#!/usr/bin/env python3
"""Embedding generation for semantic search."""
from sentence_transformers import SentenceTransformer
import chromadb
from api.logger import root_logger

# Initialize embedding model (lightweight, 384-dim)
# This will load once and be reused
embedding_model = None
chroma_client = None
article_collection = None

def init_embeddings():
    """Initialize embedding model and Chroma DB (call once at startup)."""
    global embedding_model, chroma_client, article_collection
    
    root_logger.info("Initializing embedding model and vector DB...")
    
    # Load sentence transformer model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Initialize persistent Chroma DB
    chroma_client = chromadb.PersistentClient(path="data/chroma_db")
    
    # Get or create collection for articles
    article_collection = chroma_client.get_or_create_collection(
        name="article_metadata",
        metadata={"hnsw:space": "cosine"}  # Use cosine similarity
    )
    
    root_logger.info("Embedding system initialized")

def get_article_embedding_text(article_data: dict) -> str:
    """
    Combine article metadata into a single text string for embedding.
    
    Args:
        article_data: dict with keys: title, keywords, blog_name, source, combined_score
    
    Returns:
        String for embedding generation
    """
    parts = []
    
    # Title (most important)
    if article_data.get('title'):
        parts.append(f"Title: {article_data['title']}")
    
    # Keywords (core topics)
    if article_data.get('keywords'):
        parts.append(f"Keywords: {article_data['keywords']}")
    
    # Source blog (domain authority signal)
    if article_data.get('blog_name'):
        parts.append(f"Source: {article_data['blog_name']}")
    
    # Content source type
    if article_data.get('source'):
        source_label = "Curated Blog" if article_data['source'] == 'rss' else "Community Discovery"
        parts.append(f"Type: {source_label}")
    
    # Quality score as categorical bucket
    if article_data.get('combined_score') is not None:
        score_bucket = "high_quality" if article_data['combined_score'] >= 0.6 else "standard"
        parts.append(f"Quality: {score_bucket}")
    
    return " | ".join(parts)

def update_article_embedding(article_id: int, article_data: dict):
    """
    Generate and store embedding for an article.
    
    Args:
        article_id: rowid from SQLite
        article_data: dict with article metadata
    """
    if not embedding_model or not article_collection:
        root_logger.warning("Embedding system not initialized, skipping")
        return
    
    try:
        # Generate embedding text
        text = get_article_embedding_text(article_data)
        
        # Create embedding vector
        embedding = embedding_model.encode(text).tolist()
        
        # Store in Chroma
        article_collection.upsert(
            ids=[str(article_id)],
            embeddings=[embedding],
            metadatas=[{
                "title": article_data.get('title', ''),
                "blog_name": article_data.get('blog_name', ''),
                "keywords": article_data.get('keywords', ''),
                "url": article_data.get('url', ''),
                "score": float(article_data.get('combined_score', 0))
            }]
        )
        
        root_logger.debug(f"Embedding stored for article {article_id}: {article_data.get('title', '')[:50]}")
    except Exception as e:
        root_logger.error(f"Failed to create embedding for article {article_id}: {e}", exc_info=True)

def delete_article_embedding(article_id: int):
    """Remove article embedding from vector DB (if article is deleted)."""
    if article_collection:
        try:
            article_collection.delete(ids=[str(article_id)])
            root_logger.debug(f"Embedding deleted for article {article_id}")
        except Exception as e:
            root_logger.error(f"Failed to delete embedding: {e}")

def semantic_search(query: str, limit: int = 20):
    """
    Search articles by semantic similarity using embeddings.
    
    Args:
        query: User search query
        limit: Max results to return
    
    Returns:
        List of article IDs and similarity scores
    """
    if not embedding_model or not article_collection:
        root_logger.warning("Embedding system not initialized")
        return [], []
    
    try:
        # Generate query embedding
        query_embedding = embedding_model.encode(query).tolist()
        
        # Search Chroma
        results = article_collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["metadatas", "distances"]
        )
        
        # Extract IDs and similarity scores (distance to similarity)
        article_ids = [int(id_str) for id_str in results['ids'][0]]
        similarities = [1 - dist for dist in results['distances'][0]]
        
        return article_ids, similarities
    except Exception as e:
        root_logger.error(f"Semantic search failed: {e}", exc_info=True)
        return [], []