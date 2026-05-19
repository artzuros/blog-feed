import csv
import os
from config.settings import BLOGS_CSV
from api.logger import root_logger, scan_logger

def load_blogs():
    """Load blogs from CSV file."""
    blogs = []
    scan_logger.debug(f"Loading blogs from {BLOGS_CSV}")
    
    if not os.path.exists(BLOGS_CSV):
        scan_logger.warning(f"Blogs CSV not found at {BLOGS_CSV}, creating template")
        create_template_csv()
        return []
    
    try:
        with open(BLOGS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['name'].strip()
                url = row['url'].strip()
                rss = row['rss'].strip() if row.get('rss') and row['rss'].strip() else None
                blogs.append((name, url, rss))
        
        scan_logger.info(f"Loaded {len(blogs)} blogs from {BLOGS_CSV}")
        return blogs
    except Exception as e:
        scan_logger.error(f"Error loading blogs CSV: {e}", exc_info=True)
        return []

def create_template_csv():
    """Create a template blogs.csv file."""
    os.makedirs(os.path.dirname(BLOGS_CSV), exist_ok=True)
    
    template_blogs = [
        ("Example Blog", "https://example.com/blog", "https://example.com/blog/rss.xml"),
        ("Another Blog", "https://another.com/blog", None),
    ]
    
    try:
        with open(BLOGS_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'url', 'rss'])
            for name, url, rss in template_blogs:
                writer.writerow([name, url, rss if rss else ''])
        
        scan_logger.info(f"Created template CSV at {BLOGS_CSV}")
        print(f"✅ Created template at {BLOGS_CSV}")
        print("Please edit this file with your blogs and run the scanner again.")
    except Exception as e:
        scan_logger.error(f"Failed to create template CSV: {e}", exc_info=True)

def save_blogs(blogs):
    """Save blogs to CSV file."""
    try:
        with open(BLOGS_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'url', 'rss'])
            for name, url, rss in blogs:
                writer.writerow([name, url, rss if rss else ''])
        scan_logger.info(f"Saved {len(blogs)} blogs to {BLOGS_CSV}")
    except Exception as e:
        scan_logger.error(f"Failed to save blogs: {e}", exc_info=True)

def add_blog(name, url, rss=None):
    """Add a single blog to CSV."""
    scan_logger.info(f"Adding blog: {name} ({url})")
    blogs = load_blogs()
    blogs.append((name, url, rss))
    save_blogs(blogs)
    print(f"✅ Added {name} to {BLOGS_CSV}")

def remove_blog(name):
    """Remove a blog from CSV."""
    scan_logger.info(f"Removing blog: {name}")
    blogs = load_blogs()
    filtered = [b for b in blogs if b[0] != name]
    if len(filtered) == len(blogs):
        scan_logger.warning(f"Blog '{name}' not found for removal")
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