#!/usr/bin/env python3
"""Test scoring on a single article URL."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fetcher import fetch_article_text
from quality.slop_detector import is_likely_ai_slop
from core.llm_scorer import score_with_llm
from core.keywords import extract_keywords
from api.logger import root_logger, llm_logger

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_scoring.py <article_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    root_logger.info(f"Testing scoring on URL: {url}")
    
    print(f"📥 Fetching: {url}")
    text = fetch_article_text(url)
    
    if not text or len(text) < 200:
        root_logger.warning(f"Insufficient text from {url}: {len(text) if text else 0} chars")
        print("❌ Could not extract enough text")
        sys.exit(1)
    
    root_logger.debug(f"Extracted {len(text)} characters")
    print(f"📊 Extracted {len(text)} characters")
    
    # Heuristic score
    root_logger.debug("Running heuristic scoring")
    heuristic_score, reason = is_likely_ai_slop(text)
    print(f"\n🎯 Heuristic score: {heuristic_score:.2f}")
    print(f"   Reason: {reason}")
    
    # LLM score
    print(f"\n🤖 Calling LLM (may take 10-30 seconds)...")
    llm_logger.info(f"Testing LLM scoring on {url}")
    llm_score = score_with_llm(text)
    
    if llm_score is not None:
        print(f"   LLM score: {llm_score:.2f}")
    else:
        print(f"   ❌ LLM scoring failed")
    
    # Combined
    if llm_score:
        combined = (heuristic_score * 0.6) + (llm_score * 0.4)
        print(f"\n📊 Combined score: {combined:.2f}")
    
    # Keywords
    keywords = extract_keywords(text)
    print(f"\n🏷️ Keywords: {keywords}")
    
    # Preview
    print(f"\n📄 Preview: {text[:300]}...")
    
    root_logger.info(f"Scoring test complete for {url}")

if __name__ == "__main__":
    main()