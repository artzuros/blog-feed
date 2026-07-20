"""LLM-based article scoring using DeepSeek API (OpenAI-compatible)."""
import re
from openai import OpenAI
from api.logger import llm_logger
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_MODEL


def score_with_llm(text, model=None):
    """Return a score between 0 and 1 (1 = excellent, 0 = slop)."""
    if not DEEPSEEK_API_KEY:
        llm_logger.warning("DEEPSEEK_API_KEY not set, skipping LLM scoring")
        return None

    model = model or DEEPSEEK_MODEL
    llm_logger.debug(f"Scoring with DeepSeek model: {model}, text length: {len(text)}")

    prompt = f"""Rate this engineering article on a scale 0-10 for technical depth and originality.
0-2: AI-generated fluff, SEO spam, no substance
3-5: Shallow tutorial, lacks specific details
6-8: Solid engineering with concrete examples
9-10: Exceptional depth, novel insights, production-grade

Article:
{text[:3000]}

Respond with ONLY a number (0-10)."""

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
        )
        raw = response.choices[0].message.content.strip()
        llm_logger.debug(f"DeepSeek raw response: {raw}")

        match = re.search(r'\b([0-9]|10)\b', raw)
        if match:
            score = int(match.group(1)) / 10.0
            llm_logger.info(f"LLM score: {score:.2f} for text length {len(text)}")
            return score
        else:
            llm_logger.warning(f"Could not parse DeepSeek response: {raw}")
            return 0.5
    except Exception as e:
        llm_logger.error(f"DeepSeek scoring failed: {e}", exc_info=True)
        return None
