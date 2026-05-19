#!/usr/bin/env python3
"""Interactive blog management tool."""
import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.blogs_loader import load_blogs, save_blogs, add_blog, remove_blog, list_blogs
from config.settings import BLOGS_CSV
from api.logger import scan_logger

def add_blogs_interactive():
    """Add blogs interactively."""
    scan_logger.info("Interactive blog addition started")
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
        
        try:
            add_blog(name, url, rss if rss else None)
            added += 1
            scan_logger.debug(f"Added blog: {name}")
        except Exception as e:
            scan_logger.error(f"Failed to add blog {name}: {e}", exc_info=True)
            print(f"❌ Failed to add {name}: {e}")
    
    scan_logger.info(f"Added {added} new blogs")
    print(f"\n✅ Added {added} new blog(s)")

def import_from_csv(import_file):
    """Import blogs from another CSV file."""
    scan_logger.info(f"Importing blogs from {import_file}")
    
    if not os.path.exists(import_file):
        scan_logger.error(f"Import file not found: {import_file}")
        print(f"❌ File not found: {import_file}")
        return
    
    try:
        with open(import_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            imported = 0
            for row in reader:
                name = row.get('name', '').strip()
                url = row.get('url', '').strip()
                rss = row.get('rss', '').strip()
                if name and url:
                    try:
                        add_blog(name, url, rss if rss else None)
                        imported += 1
                    except Exception as e:
                        scan_logger.error(f"Failed to import {name}: {e}")
        
        scan_logger.info(f"Imported {imported} blogs from {import_file}")
        print(f"✅ Imported {imported} blogs from {import_file}")
    except Exception as e:
        scan_logger.error(f"Failed to import CSV: {e}", exc_info=True)
        print(f"❌ Failed to import: {e}")

def export_to_csv(export_file):
    """Export blogs to CSV file."""
    scan_logger.info(f"Exporting blogs to {export_file}")
    
    blogs = load_blogs()
    try:
        with open(export_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'url', 'rss'])
            for name, url, rss in blogs:
                writer.writerow([name, url, rss if rss else ''])
        
        scan_logger.info(f"Exported {len(blogs)} blogs to {export_file}")
        print(f"✅ Exported {len(blogs)} blogs to {export_file}")
    except Exception as e:
        scan_logger.error(f"Failed to export blogs: {e}", exc_info=True)
        print(f"❌ Failed to export: {e}")

def main():
    print("\n📚 Blog Management Tool")
    print("=" * 40)
    print(f"Blogs file: {BLOGS_CSV}")
    
    scan_logger.info("Blog management tool started")
    
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
            try:
                remove_blog(name)
                scan_logger.info(f"Removed blog: {name}")
            except Exception as e:
                scan_logger.error(f"Failed to remove {name}: {e}")
                print(f"❌ Failed to remove: {e}")
        elif choice == "4":
            filepath = input("CSV file to import: ").strip()
            import_from_csv(filepath)
        elif choice == "5":
            filepath = input("Export filename (default: blogs_export.csv): ").strip()
            if not filepath:
                filepath = "blogs_export.csv"
            export_to_csv(filepath)
        elif choice == "6":
            try:
                os.system(f'open {BLOGS_CSV}' if sys.platform == 'darwin' else f'start {BLOGS_CSV}')
                scan_logger.debug(f"Opened {BLOGS_CSV} in editor")
            except Exception as e:
                scan_logger.error(f"Failed to open editor: {e}")
        elif choice == "7":
            scan_logger.info("Blog management tool exited")
            print("Goodbye!")
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()