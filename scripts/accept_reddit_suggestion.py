#!/usr/bin/env python3
"""Manually accept a Reddit suggestion and add to curated blogs."""
import sys
import json
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.logger import scan_logger

SUGGESTIONS_FILE = "data/reddit_suggestions.json"

def load_suggestions():
    scan_logger.debug(f"Loading suggestions from {SUGGESTIONS_FILE}")
    
    if not os.path.exists(SUGGESTIONS_FILE):
        scan_logger.warning(f"No suggestions file found at {SUGGESTIONS_FILE}")
        print(f"\n❌ No suggestions file found at {SUGGESTIONS_FILE}")
        print("   Run reddit_discovery.py first to generate suggestions.")
        return []
    
    try:
        with open(SUGGESTIONS_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                scan_logger.warning("Suggestions file is empty")
                return []
            suggestions = json.loads(content)
            scan_logger.debug(f"Loaded {len(suggestions)} suggestions")
            return suggestions
    except json.JSONDecodeError as e:
        scan_logger.error(f"Failed to parse suggestions JSON: {e}", exc_info=True)
        return []

def save_suggestions(suggestions):
    try:
        os.makedirs(os.path.dirname(SUGGESTIONS_FILE), exist_ok=True)
        with open(SUGGESTIONS_FILE, 'w') as f:
            json.dump(suggestions, f, indent=2)
        scan_logger.info(f"Saved {len(suggestions)} suggestions")
    except Exception as e:
        scan_logger.error(f"Failed to save suggestions: {e}", exc_info=True)

def list_pending_suggestions(suggestions, review_type=None):
    """List suggestions pending acceptance, optionally filtered by review_type."""
    if review_type:
        pending = [s for s in suggestions if s.get('reviewed') == review_type and not s.get('accepted')]
    else:
        pending = [s for s in suggestions if s.get('reviewed') in ['llm', 'manual'] and not s.get('accepted')]
    
    if not pending:
        type_label = "manually-reviewed" if review_type == 'manual' else "LLM-reviewed"
        scan_logger.debug(f"No {type_label} suggestions pending acceptance")
        print(f"\n📭 No {'manually-reviewed' if review_type == 'manual' else 'LLM-reviewed'} suggestions pending acceptance.")
        return []
    
    type_label = "Manual" if review_type == 'manual' else "LLM"
    scan_logger.info(f"Showing {len(pending)} {type_label}-reviewed suggestions")
    print(f"\n📋 {type_label}-reviewed suggestions ready for acceptance ({len(pending)}):")
    print("-" * 70)
    for i, s in enumerate(pending, 1):
        combined = s.get('combined_score', s['heuristic_score'])
        status = f"✅ Combined: {combined:.2f}" if s.get('reviewed') == 'llm' else f"📊 Heuristic: {s['heuristic_score']:.2f}"
        print(f"{i:3}. {s['domain']:35} | {status} | {s['title'][:50]}...")
    
    return pending

def accept_suggestion(suggestion):
    """Mark suggestion as accepted and return True if confirmed."""
    scan_logger.info(f"Accepting suggestion: {suggestion['domain']}")
    print(f"\n📝 Accepting: {suggestion['domain']}")
    print(f"   Title: {suggestion['title']}")
    
    if suggestion.get('reviewed') == 'llm':
        print(f"   Combined score: {suggestion.get('combined_score', suggestion['heuristic_score']):.2f}")
        print(f"   (Heuristic: {suggestion['heuristic_score']:.2f} + LLM: {suggestion.get('llm_score', 'N/A')})")
    else:
        print(f"   Heuristic score: {suggestion['heuristic_score']:.2f}")
    
    print(f"   Reddit score: {suggestion['reddit_score']} upvotes from r/{suggestion['subreddit']}")
    
    confirm = input("\nAccept this blog and add to your curated list? (y/n): ")
    if confirm.lower() == 'y':
        suggestion['accepted'] = True
        suggestion['accepted_at'] = datetime.now().isoformat()
        scan_logger.info(f"Suggestion accepted: {suggestion['domain']}")
        return True
    
    scan_logger.debug(f"Suggestion rejected: {suggestion['domain']}")
    return False

def main():
    print("=" * 50)
    print("Accept Reddit Suggestions")
    print("=" * 50)
    
    scan_logger.info("Starting accept suggestions script")
    
    suggestions = load_suggestions()
    if not suggestions:
        return
    
    # Count pending by type
    pending_llm = [s for s in suggestions if s.get('reviewed') == 'llm' and not s.get('accepted')]
    pending_manual = [s for s in suggestions if s.get('reviewed') == 'manual' and not s.get('accepted')]
    
    scan_logger.debug(f"Pending: {len(pending_llm)} LLM, {len(pending_manual)} manual")
    
    print(f"\n📊 Summary:")
    print(f"   - LLM-reviewed suggestions pending: {len(pending_llm)}")
    print(f"   - Manually-reviewed suggestions pending: {len(pending_manual)}")
    
    print("\nOptions:")
    print("  1. Show LLM-reviewed suggestions only")
    print("  2. Show manually-reviewed suggestions only")
    print("  3. Show ALL pending suggestions (both)")
    print("  4. Exit")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice == "1":
        pending = list_pending_suggestions(suggestions, 'llm')
    elif choice == "2":
        pending = list_pending_suggestions(suggestions, 'manual')
    elif choice == "3":
        pending = list_pending_suggestions(suggestions)
    else:
        scan_logger.info("User exited")
        print("Goodbye!")
        return
    
    if not pending:
        return
    
    accepted_count = 0
    for i, suggestion in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}]")
        if accept_suggestion(suggestion):
            accepted_count += 1
    
    if accepted_count > 0:
        save_suggestions(suggestions)
        scan_logger.info(f"Accepted {accepted_count} suggestions")
        print(f"\n✅ Marked {accepted_count} suggestion(s) as accepted")
        print("\n📝 Next step: Run import_reddit_to_curated.py to:")
        print("   1. Add domains to blogs.csv")
        print("   2. Fetch and score articles from these blogs")
        print("   3. Save them to blog_scout.db")
    else:
        scan_logger.debug("No suggestions accepted")
        print("\nNo suggestions accepted.")

if __name__ == "__main__":
    main()