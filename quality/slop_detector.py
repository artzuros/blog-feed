import re
import textstat
from api.logger import root_logger

def is_likely_ai_slop(text, min_quality_words=150):
    """
    Returns (slop_score, reason) where score > 0.6 suggests low-quality/AI content.
    """
    word_count = len(text.split())
    root_logger.debug(f"Detecting slop in text, length: {word_count} words")
    
    if word_count < min_quality_words:
        root_logger.debug(f"Text too short ({word_count} words), returning low slop score")
        return (0.3, f"Only {word_count} words – too short to evaluate reliably")
    
    try:
        # 1. Technical density (more is better)
        code_indicators = len(re.findall(r'\b(function|class|def|import|const|let|=>|```|implementation|pipeline|benchmark|latency|throughput|cluster|deployment|migration)\b', text, re.I))
        numbers = len(re.findall(r'\b\d+\b', text))
        technical_terms = len(re.findall(r'\b(API|database|cache|latency|throughput|cluster|pod|container|deploy|pipeline|async|thread|mutex|Kafka|Redis|PostgreSQL|Kubernetes|Docker|AWS|GCP|Azure|CI/CD|terraform)\b', text, re.I))
        
        total_signals = code_indicators + numbers + technical_terms
        density = total_signals / word_count
        density_score = min(1.0, density * 10)
        
        # 2. Generic/AI patterns
        weasel_words = [
            "in today's", "ever-evolving", "unlock the power", "delve into", "navigate the",
            "game-changer", "revolutionize", "leverage", "synergy", "unleash", "harness",
            "robust", "in this article", "by the end of", "let's dive", "to sum up"
        ]
        weasel_count = sum(text.lower().count(w) for w in weasel_words)
        weasel_score = min(1.0, weasel_count / 8)
        
        # 3. Repetitiveness
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip().lower() for s in sentences if len(s) > 20]
        if len(sentences) > 5:
            unique_ratio = len(set(sentences)) / len(sentences)
            repetition_score = 1 - unique_ratio
        else:
            repetition_score = 0
        
        # 4. Readability
        try:
            readability = textstat.flesch_reading_ease(text)
            readability_score = max(0, min(1.0, (readability - 50) / 40))
        except:
            readability_score = 0.3
        
        # Combine scores
        slop_score = (
            (1 - density_score) * 0.40 +
            weasel_score * 0.25 +
            repetition_score * 0.20 +
            readability_score * 0.15
        )
        
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
        
        reason_text = ", ".join(reasons) if reasons else "appears to be original, technical content"
        
        root_logger.debug(f"Slop score: {slop_score:.2f} - {reason_text[:100]}")
        return (slop_score, reason_text)
        
    except Exception as e:
        root_logger.error(f"Slop detection failed: {e}", exc_info=True)
        return (0.5, "Error during slop detection")