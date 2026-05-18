from fastapi import APIRouter, HTTPException, Query
from typing import List
import csv
from api.dependencies import load_blogs_csv
from api.models.schemas import BlogResponse, BlogCreate
from config.settings import BLOGS_CSV

router = APIRouter()

@router.get("/blogs", response_model=List[BlogResponse])
def get_blogs():
    """Get all curated blogs."""
    return load_blogs_csv()

@router.post("/blogs")
def add_blog(blog: BlogCreate):
    """Add a new blog to blogs.csv."""
    # Check if already exists
    existing = load_blogs_csv()
    for b in existing:
        if b['name'].lower() == blog.name.lower():
            raise HTTPException(status_code=400, detail="Blog already exists")
    
    # Append to CSV
    with open(BLOGS_CSV, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([blog.name, blog.url, blog.rss if blog.rss else ''])
    
    return {"message": f"Added {blog.name}", "blog": blog}

@router.delete("/blogs/{blog_name}")
def delete_blog(blog_name: str):
    """Remove a blog from blogs.csv."""
    blogs = load_blogs_csv()
    filtered = [b for b in blogs if b['name'].lower() != blog_name.lower()]
    
    if len(filtered) == len(blogs):
        raise HTTPException(status_code=404, detail="Blog not found")
    
    with open(BLOGS_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'url', 'rss'])
        for b in filtered:
            writer.writerow([b['name'], b['url'], b['rss'] if b['rss'] else ''])
    
    return {"message": f"Removed {blog_name}"}