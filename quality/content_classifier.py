"""
Classify article content as technical blog post vs news/marketing announcement.
Focuses on distinguishing press releases from engineering content.
"""
import re
import logging

try:
    from api.logger import root_logger
except ImportError:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    root_logger = logging.getLogger(__name__)

# Strong marketing indicators (these scream "press release / announcement")
STRONG_MARKETING = {
    'announcing': 3, 'announcement': 3, 'today we announced': 4, 'we are excited to announce': 4,
    'we\'re excited to announce': 4, 'we are proud to announce': 4, 'we\'re proud to announce': 4,
    'broken ground': 3, 'broke ground': 3, 'cutting-edge': 2, 'world-class': 2,
    'join us': 2, 'we\'re hiring': 3, 'careers': 2, 'job openings': 2,
    'funding round': 3, 'series a': 3, 'series b': 3, 'raised.*million': 3,
    'acquisition': 3, 'acquired': 3, 'partnership': 2,
    'press release': 4, 'media contact': 3,
}

# Weak marketing indicators (educational/brand content, lower weight)
WEAK_MARKETING = {
    'explain': 1, 'learn about': 1, 'what is': 1, 'introduction to': 1,
    'get started': 1, 'sign up': 1.5, 'free trial': 1.5,
    'our platform': 1, 'our product': 1, 'our solution': 1,
    'customers': 0.5, 'customer story': 1, 'testimonial': 1,
    'webinar': 1.5, 'event': 1, 'conference': 1, 'talk': 0.5,
}

# Strong technical indicators (deep engineering content)
STRONG_TECHNICAL = {
    # Specific technologies (not generic)
    'kafka': 3, 'postgres': 3, 'kubernetes': 3, 'docker': 2, 'terraform': 2,
    'redis': 2, 'mysql': 2, 'mongodb': 2, 'rabbitmq': 2, 'prometheus': 2,
    'grafana': 2, 'datadog': 2, 'nvidia': 2, 'cuda': 2,
    # Performance metrics
    'latency': 3, 'throughput': 3, 'benchmark': 3, 'percentile': 3, 'p99': 3,
    'p50': 3, 'p95': 3, 'qps': 2, 'rps': 2,
    # Architecture
    'consensus algorithm': 3, 'raft': 2, 'paxos': 2, 'vector clock': 2,
    'sharding': 2, 'partition': 1.5, 'rebalancing': 2,
    # Code/implementation
    'pull request': 2, 'pr #': 2, 'code review': 2, 'refactoring': 2,
    'debugging': 2, 'profiling': 2, 'instrumentation': 2,
}

# Weak technical indicators (can appear in marketing too)
WEAK_TECHNICAL = {
    'server': -0.5, 'database': -0.5, 'cloud': -0.5, 'api': -0.5,
    'data': -0.3, 'network': -0.3, 'infrastructure': -0.5,
    'performance': -0.5, 'scalability': -0.5, 'reliability': -0.5,
}

def has_code_blocks(text):
    """Check for actual code (strong technical signal)."""
    # Code blocks
    if re.search(r'```\w*\n[\s\S]+?\n```', text):
        return True
    # Inline code
    if re.search(r'`[^`]{5,}`', text):  # longer than 5 chars
        return True
    # Code tags
    if '<code>' in text or '<pre>' in text:
        return True
    return False

def has_numbers_and_units(text):
    """Check for technical numbers with units."""
    patterns = [
        r'\d+\s*(ms|millisecond)', r'\d+\s*(gb|gigabyte)', r'\d+\s*(tb|terabyte)',
        r'\d+\s*(req/s|rps|qps)', r'\d+\s*(mb/s|mbps)', r'\d+%',
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.I):
            return True
    return False

def is_marketing_or_news(title, text, threshold=0.6):
    """Return (score, reason) where score > threshold indicates marketing/news."""
    if not text or len(text) < 200:
        return 0.5, "Too short to classify reliably"
    
    combined = (title + " " + text).lower()
    
    # Calculate scores
    marketing_score = 0
    tech_score = 0
    marketing_terms = []
    tech_terms = []
    
    # Strong marketing
    for word, weight in STRONG_MARKETING.items():
        if word in combined:
            count = combined.count(word)
            marketing_score += count * weight
            if len(marketing_terms) < 5:
                marketing_terms.append((word, count))
    
    # Weak marketing
    for word, weight in WEAK_MARKETING.items():
        if word in combined:
            count = combined.count(word)
            marketing_score += count * weight
            if len(marketing_terms) < 5:
                marketing_terms.append((word, count))
    
    # Strong technical
    for word, weight in STRONG_TECHNICAL.items():
        if word in combined:
            count = combined.count(word)
            tech_score += count * weight
            if len(tech_terms) < 5:
                tech_terms.append((word, count))
    
    # Weak technical (negative marketing score)
    for word, weight in WEAK_TECHNICAL.items():
        if word in combined:
            count = combined.count(word)
            marketing_score += count * weight
    
    # Code presence is strong technical signal
    has_code = has_code_blocks(text)
    if has_code:
        tech_score += 5
    
    # Numbers with units are technical
    if has_numbers_and_units(text):
        tech_score += 2
    
    # Calculate final score (sigmoid on marketing - tech)
    raw_signal = marketing_score - tech_score
    # Scale raw_signal: typical range -10 to +15
    score = 1 / (1 + (2.71828 ** (-raw_signal / 3)))
    score = max(0.0, min(1.0, score))
    
    # Build reason
    reasons = []
    if marketing_terms:
        reasons.append(f"marketing: {', '.join([w for w,_ in marketing_terms[:3]])}")
    if tech_terms:
        reasons.append(f"technical: {', '.join([w for w,_ in tech_terms[:3]])}")
    if has_code:
        reasons.append("has code blocks")
    if not reasons:
        reasons.append("no strong signals")
    
    return score, ", ".join(reasons)

if __name__ == "__main__":
    # Test 1: Meta marketing article
    title = "Meta Data Center Announcement"
    text = """At Meta, we've been building and operating our data center fleet for over a decade. In the last twenty-four months, we've broken ground on ten data centers as we continue to expand our fleet of cutting-edge, AI-optimized facilities designed to manage our AI workloads and other technologies.

We're here to explain what data centers are and how they help you connect to your favorite digital experiences, from conversations with Meta AI and reaching new customers through an Instagram ad to navigating the world with your RayBan Meta glasses.

What Is a Data Center?
A data center is a physical building that houses technology to rapidly process digital information..."""
    
    score, reason = is_marketing_or_news(title, text)
    print(f"Meta marketing article -> Score: {score:.2f} - {reason}")
    
    # Test 2: Technical Kafka article
    title = "How we reduced Kafka latency by 60%"
    text = """We tuned fetch.min.bytes and partition count from 6 to 18. The consumer group rebalance protocol was the bottleneck. Here's the exact configuration change: `fetch.min.bytes=50000`. Throughput went from 200 req/s to 1200 req/s. P99 latency dropped from 200ms to 45ms."""
    
    score, reason = is_marketing_or_news(title, text)
    print(f"Technical Kafka article -> Score: {score:.2f} - {reason}")
    
    # Test 3: Educational but not marketing
    title = "Understanding database indexes"
    text = """A database index is a data structure that improves the speed of data retrieval operations on a database table. B-trees are the most common index structure. Here's how to create an index: `CREATE INDEX idx_name ON table(column)`."""
    
    score, reason = is_marketing_or_news(title, text)
    print(f"Educational article -> Score: {score:.2f} - {reason}")