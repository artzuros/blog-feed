import ollama
import re

def score_with_llm(text, model="mistral"):
    """Return a score between 0 and 1 (1 = excellent, 0 = slop)."""
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
        # Extract first number
        match = re.search(r'\b([0-9]|10)\b', raw)
        if match:
            score = int(match.group(1)) / 10.0
            return score
        else:
            return 0.5  # fallback
    except Exception as e:
        print(f"LLM scoring failed: {e}")
        return None