import re
import math
from collections import defaultdict, Counter
from api.logger import root_logger

# Extended stopwords (common English + programming noise)
STOPWORDS = {
    'the', 'a', 'an', 'and', 'of', 'to', 'in', 'for', 'on', 'with', 'by',
    'is', 'are', 'that', 'this', 'these', 'those', 'be', 'from', 'at', 'as',
    'or', 'but', 'not', 'can', 'will', 'have', 'has', 'could', 'should', 'would',
    'i', 'you', 'we', 'they', 'he', 'she', 'it', 'was', 'were', 'been', 'being',
    'my', 'your', 'their', 'our', 'its', 'then', 'than', 'so', 'too', 'also',
    'very', 'just', 'but', 'do', 'does', 'did', 'doing', 'get', 'gets', 'got',
    'go', 'goes', 'going', 'make', 'makes', 'made', 'making', 'use', 'uses',
    'used', 'using', 'see', 'sees', 'saw', 'seeing', 'like', 'likes', 'liked',
    'know', 'knows', 'knew', 'knowing', 'think', 'thinks', 'thought', 'thinking',
    # technical noise
    'http', 'https', 'www', 'com', 'io', 'org', 'net', 'html', 'php', 'asp'
}

# Common technical keywords to boost (lowercase)
TECH_BOOST = {
    'api', 'sdk', 'cli', 'ui', 'ux', 'db', 'sql', 'nosql', 'cache', 'redis',
    'postgres', 'mysql', 'mongodb', 'kafka', 'rabbitmq', 'kubernetes', 'docker',
    'terraform', 'aws', 'gcp', 'azure', 'ci', 'cd', 'devops', 'sre', 'llm',
    'gpu', 'cpu', 'memory', 'latency', 'throughput', 'scalability', 'reliability',
    'deployment', 'migration', 'rollback', 'monitoring', 'observability', 'logging',
    'authentication', 'authorization', 'encryption', 'hashing', 'index', 'join',
    'replication', 'sharding', 'partition', 'queue', 'pubsub', 'websocket',
    'middleware', 'proxy', 'loadbalancer', 'firewall', 'cdn', 'dns', 'tcp', 'udp',
    'http2', 'grpc', 'rest', 'graphql', 'oauth', 'jwt', 'pipeline', 'automation',
    'orchestration', 'serverless', 'function', 'lambda', 'container', 'pod',
    'service', 'ingress', 'configmap', 'secret', 'volume', 'storage', 'backup'
}

def preprocess_text(text: str) -> str:
    """Clean and normalize text for keyword extraction."""
    # Remove URLs and common HTML tags
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    # Remove punctuation and digits (but keep hyphens inside words)
    text = re.sub(r'[^\w\s-]', ' ', text)
    # Replace newlines and multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def split_to_phrases(tokens, stopwords):
    """Split token list into candidate phrases based on stopwords."""
    phrases = []
    current_phrase = []
    for word in tokens:
        if word in stopwords or len(word) < 3:
            if current_phrase:
                phrases.append(' '.join(current_phrase))
                current_phrase = []
        else:
            current_phrase.append(word)
    if current_phrase:
        phrases.append(' '.join(current_phrase))
    return [p for p in phrases if len(p.split()) <= 4]  # limit phrase length

def calculate_word_scores(phrases):
    """Calculate RAKE word scores: deg(w) / freq(w)."""
    word_freq = defaultdict(int)
    word_deg = defaultdict(int)
    for phrase in phrases:
        words = phrase.split()
        word_set = set(words)
        for w in words:
            word_freq[w] += 1
        for w in word_set:
            word_deg[w] += len(word_set)  # degree = number of distinct co-occurring words in phrase
    word_scores = {}
    for w in word_freq:
        word_scores[w] = word_deg[w] / word_freq[w]
    return word_scores

def score_phrases(phrases, word_scores):
    """Score each phrase as sum of word scores."""
    phrase_scores = {}
    for phrase in phrases:
        words = phrase.split()
        if not words:
            continue
        score = sum(word_scores.get(w, 0) for w in words)
        # Boost for longer phrases and technical terms
        length_boost = 1 + (len(words) - 1) * 0.2
        tech_boost = 1 + sum(0.5 for w in words if w in TECH_BOOST)
        phrase_scores[phrase] = score * length_boost * tech_boost
    return phrase_scores

def extract_keywords(text, top_n=10):
    """
    Extract keywords using RAKE with technical term boosting.
    Returns a comma-separated string of top keywords.
    """
    root_logger.debug(f"Extracting keywords from text length {len(text)}")
    if not text or len(text) < 100:
        return ""
    
    try:
        # Preprocess
        cleaned = preprocess_text(text)
        # Tokenize
        tokens = cleaned.split()
        # Build stopwords set (add program-specific ones)
        stopwords = STOPWORDS.copy()
        stopwords.update({'using', 'also', 'however', 'therefore', 'thus', 'hence'})
        # Split into candidate phrases
        phrases = split_to_phrases(tokens, stopwords)
        if not phrases:
            root_logger.warning("No phrases found for keyword extraction")
            return ""
        # Calculate word scores
        word_scores = calculate_word_scores(phrases)
        # Score phrases
        phrase_scores = score_phrases(phrases, word_scores)
        # Sort and take top_n
        sorted_phrases = sorted(phrase_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        keywords = ', '.join([p for p, _ in sorted_phrases])
        root_logger.debug(f"Extracted {len(sorted_phrases)} keywords: {keywords[:100]}")
        return keywords
    except Exception as e:
        root_logger.error(f"Keyword extraction failed: {e}", exc_info=True)
        return ""