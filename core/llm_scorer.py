import ollama
import re
from api.logger import llm_logger

def score_with_llm(text, model="granite3.3:2b"):
    """Return a score between 0 and 1 (1 = excellent, 0 = slop)."""
    llm_logger.debug(f"Scoring with LLM model: {model}, text length: {len(text)}")
    
    prompt = f"""Rate this engineering article on a scale 0-10 for technical depth and originality.
0-2: AI-generated fluff, SEO spam, no substance
3-5: Shallow tutorial, lacks specific details
6-8: Solid engineering with concrete examples
9-10: Exceptional depth, novel insights, production-grade

Article:
{text[:3000]}

Respond with ONLY a number (0-10)."""
    
    try:
        response = ollama.generate(model=model, prompt=prompt)
        raw = response['response'].strip()
        llm_logger.debug(f"LLM raw response: {raw}")
        
        # Extract first number
        match = re.search(r'\b([0-9]|10)\b', raw)
        if match:
            score = int(match.group(1)) / 10.0
            llm_logger.info(f"LLM score: {score:.2f} for text length {len(text)}")
            return score
        else:
            llm_logger.warning(f"Could not parse LLM response: {raw}")
            return 0.5  # fallback
    except Exception as e:
        llm_logger.error(f"LLM scoring failed: {e}", exc_info=True)
        return None