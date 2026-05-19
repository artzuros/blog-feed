from fastapi import APIRouter, HTTPException, Depends
from typing import List
import csv
import os
from api.dependencies import load_blogs_csv
from api.models.schemas import BlogResponse, BlogCreate
from api.auth import verify_admin_key
from api.logger import root_logger
from config.settings import BLOGS_CSV

router = APIRouter(dependencies=[Depends(verify_admin_key)])

@router.get("/blogs", response_model=List[BlogResponse], dependencies=[])
def get_blogs():
    root_logger.info("GET /blogs called")
    blogs = load_blogs_csv()
    root_logger.debug(f"Returning {len(blogs)} blogs")
    return blogs

@router.post("/blogs")
def add_blog(blog: BlogCreate):
    root_logger.info(f"POST /blogs called for {blog.name}")
    existing = load_blogs_csv()
    for b in existing:
        if b['name'].lower() == blog.name.lower():
            root_logger.warning(f"Blog already exists: {blog.name}")
            raise HTTPException(status_code=400, detail="Blog already exists")
    
    os.makedirs(os.path.dirname(BLOGS_CSV), exist_ok=True)
    file_exists = os.path.exists(BLOGS_CSV)
    
    with open(BLOGS_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['name', 'url', 'rss'])
        writer.writerow([blog.name, blog.url, blog.rss if blog.rss else ''])
    
    root_logger.info(f"Added blog: {blog.name} ({blog.url})")
    return {"message": f"Added {blog.name}", "blog": blog}

@router.delete("/blogs/{blog_name}")
def delete_blog(blog_name: str):
    root_logger.info(f"DELETE /blogs/{blog_name} called")
    if not os.path.exists(BLOGS_CSV):
        root_logger.error(f"Blogs file not found")
        raise HTTPException(status_code=404, detail="Blogs file not found")
    
    blogs = load_blogs_csv()
    filtered = [b for b in blogs if b['name'].lower() != blog_name.lower()]
    if len(filtered) == len(blogs):
        root_logger.warning(f"Blog not found: {blog_name}")
        raise HTTPException(status_code=404, detail="Blog not found")
    
    with open(BLOGS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'url', 'rss'])
        for b in filtered:
            writer.writerow([b['name'], b['url'], b['rss'] if b['rss'] else ''])
    
    root_logger.info(f"Deleted blog: {blog_name}")
    return {"message": f"Removed {blog_name}"}

@router.post("/blogs/refresh")
def refresh_blogs():
    root_logger.info("POST /blogs/refresh called - manual scan triggered")
    import subprocess
    try:
        result = subprocess.run(
            ['python', 'scripts/scheduled_scan.py'],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            root_logger.info("Manual scan completed successfully")
        else:
            root_logger.error(f"Manual scan failed with code {result.returncode}: {result.stderr}")
        return {
            "message": "Blog refresh completed",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        root_logger.error("Manual scan timed out after 10 minutes")
        raise HTTPException(status_code=504, detail="Refresh timed out after 10 minutes")
    except Exception as e:
        root_logger.error(f"Manual scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

@router.get("/admin/verify")
def verify_admin_key(api_key: str = Depends(verify_admin_key)):
    root_logger.info("Admin verification endpoint called")
    return {"valid": True, "message": "API key is valid"}