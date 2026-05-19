from fastapi import APIRouter, HTTPException, Depends
from typing import List
import csv
import os
from api.dependencies import load_blogs_csv
from api.models.schemas import BlogResponse, BlogCreate
from api.auth import verify_admin_key
from config.settings import BLOGS_CSV

router = APIRouter(dependencies=[Depends(verify_admin_key)])  # All routes in this router require API key

@router.get("/blogs", response_model=List[BlogResponse], dependencies=[])  # Public read
def get_blogs():
    """Get all curated blogs (no auth required)."""
    return load_blogs_csv()

@router.post("/blogs")
def add_blog(blog: BlogCreate):
    """Add a new blog to blogs.csv (admin only)."""
    existing = load_blogs_csv()
    for b in existing:
        if b['name'].lower() == blog.name.lower():
            raise HTTPException(status_code=400, detail="Blog already exists")
    
    os.makedirs(os.path.dirname(BLOGS_CSV), exist_ok=True)
    file_exists = os.path.exists(BLOGS_CSV)
    
    with open(BLOGS_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['name', 'url', 'rss'])
        writer.writerow([blog.name, blog.url, blog.rss if blog.rss else ''])
    
    return {"message": f"Added {blog.name}", "blog": blog}

@router.delete("/blogs/{blog_name}")
def delete_blog(blog_name: str):
    if not os.path.exists(BLOGS_CSV):
        raise HTTPException(status_code=404, detail="Blogs file not found")
    
    blogs = load_blogs_csv()
    filtered = [b for b in blogs if b['name'].lower() != blog_name.lower()]
    if len(filtered) == len(blogs):
        raise HTTPException(status_code=404, detail="Blog not found")
    
    with open(BLOGS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'url', 'rss'])
        for b in filtered:
            writer.writerow([b['name'], b['url'], b['rss'] if b['rss'] else ''])
    
    return {"message": f"Removed {blog_name}"}

@router.post("/blogs/refresh")
def refresh_blogs():
    import subprocess
    try:
        result = subprocess.run(
            ['python', 'scripts/scheduled_scan.py'],
            capture_output=True,
            text=True,
            timeout=600
        )
        return {
            "message": "Blog refresh completed",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Refresh timed out after 10 minutes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")