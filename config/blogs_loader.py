#!/usr/bin/env python3
"""Load blogs from CSV file."""
import csv
import os
from config.settings import BLOGS_CSV

def load_blogs():
    """Load blogs from CSV file."""
    blogs = []
    
    if not os.path.exists(BLOGS_CSV):
        print(f"⚠️ Blogs CSV not found at {BLOGS_CSV}")
        print("Creating template blogs.csv...")
        create_template_csv()
        return []
    
    with open(BLOGS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['name'].strip()
            url = row['url'].strip()
            rss = row['rss'].strip() if row.get('rss') and row['rss'].strip() else None
            blogs.append((name, url, rss))
    
    return blogs

def create_template_csv():
    """Create a template blogs.csv file."""
    os.makedirs(os.path.dirname(BLOGS_CSV), exist_ok=True)
    
    template_blogs = [
        ("Example Blog", "https://example.com/blog", "https://example.com/blog/rss.xml"),
        ("Another Blog", "https://another.com/blog", None),
    ]
    
    with open(BLOGS_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'url', 'rss'])
        for name, url, rss in template_blogs:
            writer.writerow([name, url, rss if rss else ''])
    
    print(f"✅ Created template at {BLOGS_CSV}")
    print("Please edit this file with your blogs and run the scanner again.")

def save_blogs(blogs):
    """Save blogs to CSV file."""
    with open(BLOGS_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'url', 'rss'])
        for name, url, rss in blogs:
            writer.writerow([name, url, rss if rss else ''])

def add_blog(name, url, rss=None):
    """Add a single blog to CSV."""
    blogs = load_blogs()
    blogs.append((name, url, rss))
    save_blogs(blogs)
    print(f"✅ Added {name} to {BLOGS_CSV}")

def remove_blog(name):
    """Remove a blog from CSV."""
    blogs = load_blogs()
    filtered = [b for b in blogs if b[0] != name]
    if len(filtered) == len(blogs):
        print(f"❌ Blog '{name}' not found")
        return False
    save_blogs(filtered)
    print(f"✅ Removed {name} from {BLOGS_CSV}")
    return True

def list_blogs():
    """List all blogs."""
    blogs = load_blogs()
    if not blogs:
        print("No blogs found.")
        return
    print(f"\n📚 Total blogs: {len(blogs)}")
    print("-" * 60)
    for i, (name, url, rss) in enumerate(blogs, 1):
        rss_status = "✅ RSS" if rss else "🔍 HTML only"
        print(f"{i:3}. {name:20} | {rss_status:10} | {url}")