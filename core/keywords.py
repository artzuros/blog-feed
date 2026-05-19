import re
from collections import Counter
from api.logger import root_logger

STOPWORDS = {'the', 'a', 'an', 'and', 'of', 'to', 'in', 'for', 'on', 'with', 'by', 
             'is', 'are', 'that', 'this', 'these', 'those', 'be', 'from', 'at', 'as', 
             'or', 'but', 'not', 'can', 'will', 'have', 'has', 'could', 'should', 'would'}

def extract_keywords(text, top_n=10):
    """Simple keyword extraction using frequency and technical terms."""
    root_logger.debug(f"Extracting keywords from text length {len(text)}")
    
    try:
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]
        common = Counter(filtered).most_common(top_n)
        keywords = ', '.join([w for w, _ in common])
        
        root_logger.debug(f"Extracted {len(common)} keywords: {keywords[:100]}")
        return keywords
    except Exception as e:
        root_logger.error(f"Keyword extraction failed: {e}", exc_info=True)
        return ""