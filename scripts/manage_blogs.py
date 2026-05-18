#!/usr/bin/env python3
"""Interactive blog management tool."""
import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.blogs_loader import load_blogs, save_blogs, add_blog, remove_blog, list_blogs
from config.settings import BLOGS_CSV

def add_blogs_interactive():
    """Add blogs interactively."""
    print("\n📝 Add New Blogs")
    print("Enter blog details (leave name empty to finish)")
    print("-" * 40)
    
    added = 0
    while True:
        name = input("\nBlog name (or Enter to finish): ").strip()
        if not name:
            break
        
        url = input("Blog URL: ").strip()
        rss = input("RSS URL (optional, press Enter to skip): ").strip()
        
        add_blog(name, url, rss if rss else None)
        added += 1
    
    print(f"\n✅ Added {added} new blog(s)")

def import_from_csv(import_file):
    """Import blogs from another CSV file."""
    if not os.path.exists(import_file):
        print(f"❌ File not found: {import_file}")
        return
    
    with open(import_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        imported = 0
        for row in reader:
            name = row.get('name', '').strip()
            url = row.get('url', '').strip()
            rss = row.get('rss', '').strip()
            if name and url:
                add_blog(name, url, rss if rss else None)
                imported += 1
    
    print(f"✅ Imported {imported} blogs from {import_file}")

def export_to_csv(export_file):
    """Export blogs to CSV file."""
    blogs = load_blogs()
    with open(export_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'url', 'rss'])
        for name, url, rss in blogs:
            writer.writerow([name, url, rss if rss else ''])
    
    print(f"✅ Exported {len(blogs)} blogs to {export_file}")

def main():
    print("\n📚 Blog Management Tool")
    print("=" * 40)
    print(f"Blogs file: {BLOGS_CSV}")
    
    while True:
        print("\nOptions:")
        print("  1. List all blogs")
        print("  2. Add new blogs (interactive)")
        print("  3. Remove a blog")
        print("  4. Import from CSV")
        print("  5. Export to CSV")
        print("  6. Open blogs.csv in editor")
        print("  7. Exit")
        
        choice = input("\nChoice (1-7): ").strip()
        
        if choice == "1":
            list_blogs()
        elif choice == "2":
            add_blogs_interactive()
        elif choice == "3":
            name = input("Blog name to remove: ").strip()
            remove_blog(name)
        elif choice == "4":
            filepath = input("CSV file to import: ").strip()
            import_from_csv(filepath)
        elif choice == "5":
            filepath = input("Export filename (default: blogs_export.csv): ").strip()
            if not filepath:
                filepath = "blogs_export.csv"
            export_to_csv(filepath)
        elif choice == "6":
            os.system(f'open {BLOGS_CSV}' if sys.platform == 'darwin' else f'start {BLOGS_CSV}')
        elif choice == "7":
            print("Goodbye!")
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()