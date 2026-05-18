import re
from collections import Counter

STOPWORDS = {'the', 'a', 'an', 'and', 'of', 'to', 'in', 'for', 'on', 'with', 'by', 'is', 'are', 'that', 'this', 'these', 'those', 'be', 'from', 'at', 'as', 'or', 'but', 'not', 'can', 'will', 'have', 'has', 'could', 'should', 'would'}

def extract_keywords(text, top_n=10):
    """Simple TF-IDF-free keyword extraction using frequency and technical terms."""
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]
    common = Counter(filtered).most_common(top_n)
    return ', '.join([w for w, _ in common])