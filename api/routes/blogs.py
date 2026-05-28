from fastapi import APIRouter, HTTPException, Depends
from typing import List
import csv
import os
import subprocess
from api.dependencies import load_blogs_csv
from api.models.schemas import BlogResponse, BlogCreate
from api.auth import verify_admin_key
from api.logger import api_logger, root_logger
from config.settings import BLOGS_CSV, CACHE_FILE
import json

router = APIRouter(dependencies=[Depends(verify_admin_key)])

@router.get("/blogs", response_model=List[BlogResponse], dependencies=[])
def get_blogs():
    api_logger.info("GET /blogs - Fetching all blogs")
    blogs = load_blogs_csv()
    api_logger.debug(f"Returning {len(blogs)} blogs")
    return blogs

@router.post("/blogs")
def add_blog(blog: BlogCreate):
    api_logger.info(f"POST /blogs - Adding new blog: {blog.name} (URL: {blog.url})")
    
    existing = load_blogs_csv()
    for b in existing:
        if b['name'].lower() == blog.name.lower():
            api_logger.warning(f"Attempt to add duplicate blog: {blog.name}")
            raise HTTPException(status_code=400, detail="Blog already exists")
    
    try:
        os.makedirs(os.path.dirname(BLOGS_CSV), exist_ok=True)
        file_exists = os.path.exists(BLOGS_CSV)
        
        with open(BLOGS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['name', 'url', 'rss'])
                api_logger.debug(f"Created new blogs CSV file at {BLOGS_CSV}")
            writer.writerow([blog.name, blog.url, blog.rss if blog.rss else ''])
        
        api_logger.info(f"Successfully added blog: {blog.name}")
        return {"message": f"Added {blog.name}", "blog": blog}
    except Exception as e:
        api_logger.error(f"Failed to add blog {blog.name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add blog: {str(e)}")

@router.delete("/blogs/{blog_name}")
def delete_blog(blog_name: str):
    api_logger.info(f"DELETE /blogs/{blog_name} - Deleting blog")
    
    if not os.path.exists(BLOGS_CSV):
        api_logger.error(f"Blogs file not found at {BLOGS_CSV}")
        raise HTTPException(status_code=404, detail="Blogs file not found")
    
    try:
        blogs = load_blogs_csv()
        filtered = [b for b in blogs if b['name'].lower() != blog_name.lower()]
        
        if len(filtered) == len(blogs):
            api_logger.warning(f"Blog not found for deletion: {blog_name}")
            raise HTTPException(status_code=404, detail="Blog not found")
        
        with open(BLOGS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'url', 'rss'])
            for b in filtered:
                writer.writerow([b['name'], b['url'], b['rss'] if b['rss'] else ''])
        
        api_logger.info(f"Successfully deleted blog: {blog_name}")
        return {"message": f"Removed {blog_name}"}
    except Exception as e:
        api_logger.error(f"Failed to delete blog {blog_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete blog: {str(e)}")

@router.post("/blogs/refresh")
def refresh_blogs():
    api_logger.info("POST /blogs/refresh - Manual scan triggered")
    
    try:
        result = subprocess.run(
            ['python', 'scripts/scheduled_scan.py'],
            capture_output=True,
            text=True,
            timeout=1200
        )
        if result.returncode == 0:
            api_logger.info("Manual scan completed successfully")
        else:
            api_logger.error(f"Manual scan failed with code {result.returncode}")
            api_logger.debug(f"Scan stderr: {result.stderr[:500]}")
        
        return {
            "message": "Blog refresh completed",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        api_logger.error("Manual scan timed out after 10 minutes")
        raise HTTPException(status_code=504, detail="Refresh timed out after 10 minutes")
    except Exception as e:
        api_logger.error(f"Manual scan failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

@router.get("/admin/verify")
def verify_admin_key_endpoint(api_key: str = Depends(verify_admin_key)):
    api_logger.info("Admin verification endpoint called - key validated")
    return {"valid": True, "message": "API key is valid"}

# Cache utility functions (moved from inline)
def load_cache():
    """Load blog discovery cache from JSON file."""
    from api.logger import db_logger
    db_logger.debug(f"Loading cache from {CACHE_FILE}")
    
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
            db_logger.debug(f"Cache loaded with {len(cache)} entries")
            return cache
        except Exception as e:
            db_logger.error(f"Error loading cache: {e}", exc_info=True)
            return {}
    return {}

def save_cache(cache):
    """Save blog discovery cache to JSON file."""
    from api.logger import db_logger
    
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        db_logger.debug(f"Cache saved with {len(cache)} entries")
    except Exception as e:
        db_logger.error(f"Error saving cache: {e}", exc_info=True)