import re
import textstat

def is_likely_ai_slop(text, min_quality_words=150):
    """
    Returns (slop_score, reason) where score > 0.6 suggests low-quality/AI content.
    """
    word_count = len(text.split())
    
    if word_count < min_quality_words:
        return (0.3, f"Only {word_count} words – too short to evaluate reliably")
    
    # 1. Technical density (more is better)
    code_indicators = len(re.findall(r'\b(function|class|def|import|const|let|=>|```|implementation|pipeline|benchmark|latency|throughput|cluster|deployment|migration)\b', text, re.I))
    numbers = len(re.findall(r'\b\d+\b', text))
    technical_terms = len(re.findall(r'\b(API|database|cache|latency|throughput|cluster|pod|container|deploy|pipeline|async|thread|mutex|Kafka|Redis|PostgreSQL|Kubernetes|Docker|AWS|GCP|Azure|CI/CD|terraform)\b', text, re.I))
    
    total_signals = code_indicators + numbers + technical_terms
    density = total_signals / word_count
    # density of 0.10 = 10 signals per 100 words (very technical)
    # density of 0.01 = 1 signal per 100 words (very vague)
    density_score = min(1.0, density * 10)  # Scale: 0.1 density = 1.0 score
    
    # 2. Generic/AI patterns
    weasel_words = [
        "in today's", "ever-evolving", "unlock the power", "delve into", "navigate the",
        "game-changer", "revolutionize", "leverage", "synergy", "unleash", "harness",
        "robust", "in this article", "by the end of", "let's dive", "to sum up"
    ]
    weasel_count = sum(text.lower().count(w) for w in weasel_words)
    weasel_score = min(1.0, weasel_count / 8)  # >8 weasel phrases = high slop
    
    # 3. Repetitiveness
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip().lower() for s in sentences if len(s) > 20]
    if len(sentences) > 5:
        unique_ratio = len(set(sentences)) / len(sentences)
        repetition_score = 1 - unique_ratio
    else:
        repetition_score = 0
    
    # 4. Readability (very high readability often means oversimplified)
    try:
        readability = textstat.flesch_reading_ease(text)
        # Flesch > 70 = very easy to read (often shallow tutorials)
        readability_score = max(0, min(1.0, (readability - 50) / 40))
    except:
        readability_score = 0.3
    
    # Combine scores (lower density = higher slop, hence 1-density)
    slop_score = (
        (1 - density_score) * 0.40 +      # Low technical density is the biggest red flag
        weasel_score * 0.25 +             # Marketing/weasel words
        repetition_score * 0.20 +         # Repetitive phrasing
        readability_score * 0.15          # Oversimplified text
    )
    
    # Clamp to 0-1 range
    slop_score = min(1.0, max(0.0, slop_score))
    
    reasons = []
    if density_score < 0.3:
        reasons.append(f"very low technical density ({total_signals} signals in {word_count} words)")
    if weasel_count > 5:
        reasons.append(f"{weasel_count} generic/AI marketing phrases")
    if repetition_score > 0.4:
        reasons.append("high sentence repetition")
    if readability_score > 0.7:
        reasons.append("text is oversimplified (too easy to read)")
    
    return (slop_score, ", ".join(reasons) if reasons else "appears to be original, technical content")

if __name__ == "__main__":
    test_samples = [
        ("AI slop", "In today's ever-evolving digital landscape, unlocking the power of AI is a game-changer. In this article, we'll delve into the robust synergy between machine learning and the cloud. By the end of this post, you'll navigate the journey to unleash innovation."),
        ("Good technical", "We reduced Kafka latency from 200ms to 45ms by tuning `fetch.min.bytes` and increasing partition count from 6 to 18. The consumer group rebalance protocol was the bottleneck. Here's the exact configuration change and the Grafana dashboard before/after."),
        ("Short but good", "Fixed a production deadlock by replacing a synchronized block with a ReentrantLock. throughput went from 200 req/s to 1200 req/s.")
    ]
    
    for name, text in test_samples:
        score, reason = is_likely_ai_slop(text)
        print(f"\n{name}: score={score:.2f} – {reason}")