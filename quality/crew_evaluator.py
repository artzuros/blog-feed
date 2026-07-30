"""CrewAI multi-agent article evaluation system.

Uses 4 specialized agents running sequentially to evaluate an article across
multiple dimensions and produce a structured, explainable verdict.

Agents:
  1. Content Classifier  — article type + topic tags
  2. Technical Analyst   — depth, code, benchmarks, practical value
  3. Authenticity Judge  — marketing bias, originality, author perspective
  4. Synthesis Editor    — combines all signals into final score + reasoning

Usage:
    from quality.crew_evaluator import run_evaluation
    result = run_evaluation("Article Title", "Full article text...")
    print(result.overall_score, result.reasoning)
"""
import json
import logging
from typing import Optional

from api.logger import llm_logger
from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)


# ── LLM Setup ────────────────────────────────────────────────────────

def create_llm():
    """Configure DeepSeek via LiteLLM for CrewAI agents."""
    from crewai.llm import LLM
    if not DEEPSEEK_API_KEY:
        llm_logger.warning("DEEPSEEK_API_KEY not set — agents will fail")
    return LLM(
        model=f"deepseek/{DEEPSEEK_MODEL}",
        base_url="https://api.deepseek.com",
        api_key=DEEPSEEK_API_KEY or "",
        temperature=0.2,
    )


# ── Agent Definitions ─────────────────────────────────────────────────

def create_agents(llm):
    """Create the 4 specialized evaluation agents."""
    from crewai import Agent
    classifier = Agent(
        role="Content Classification Specialist",
        goal="Identify the article's content type and extract key topic tags",
        backstory=(
            "You are a senior editor who has classified thousands of engineering "
            "articles. You can instantly tell whether something is a deep tutorial, "
            "a research paper summary, a vendor announcement, a case study, or "
            "generic marketing fluff. You have a knack for distilling an article's "
            "core topics into 3-6 precise tags."
        ),
        llm=llm,
        verbose=True,
    )

    analyst = Agent(
        role="Senior Technical Analyst",
        goal="Evaluate the article's technical depth, code quality, "
             "performance data, and practical takeaway value",
        backstory=(
            "You are a staff engineer with 15 years of experience across "
            "infrastructure, backend systems, and distributed computing. You judge "
            "articles by their technical rigor — does the author show real "
            "architecture decisions? Are there actual code snippets, configs, or "
            "commands the reader can use? Do they cite real metrics like latency, "
            "throughput, or cost? You are unimpressed by buzzwords and impressed "
            "by specific, reproducible details."
        ),
        llm=llm,
        verbose=True,
    )

    judge = Agent(
        role="Editorial Authenticity Judge",
        goal="Detect marketing bias, assess originality, and determine "
             "whether the author is a practicing engineer",
        backstory=(
            "You have a finely-tuned BS detector. After years of reading tech "
            "content, you can smell a vendor-backed press release from the first "
            "paragraph. You distinguish between 'this is how we solved X at scale' "
            "(practitioner) and 'our platform enables X' (evangelist). You also "
            "have a strong sense of what's genuinely novel versus what's been "
            "written a hundred times before."
        ),
        llm=llm,
        verbose=True,
    )

    editor = Agent(
        role="Editor-in-Chief",
        goal="Synthesize all evaluation signals into a fair, justified "
             "final score and actionable reasoning",
        backstory=(
            "You are the final decision-maker at a respected engineering blog. "
            "Your job is to weigh the classifier's type assessment, the analyst's "
            "depth evaluation, and the authenticity judge's bias reading into a "
            "single coherent verdict. You are fair — you recognize that a tutorial "
            "can score low on originality but high on practical value. You are "
            "ruthless about marketing fluff masquerading as engineering content. "
            "Your overall_score should heavily weight technical_depth, originality, "
            "and practical_value while penalizing high marketing_bias."
        ),
        llm=llm,
        verbose=True,
    )

    return classifier, analyst, judge, editor


# ── Task Definitions ──────────────────────────────────────────────────

def create_tasks(agents, article_text, article_title):
    """Create the 4 evaluation tasks that run sequentially.

    Each task receives the article + outputs from all previous tasks as context.
    """
    from crewai import Task
    classifier, analyst, judge, editor = agents

    classify_task = Task(
        description=(
            f"Read this article and classify it:\n\n"
            f"Title: {article_title}\n\n"
            f"Text:\n{article_text[:6000]}\n\n"
            f"Determine:\n"
            f"1. content_type — one of: tutorial, case_study, research, "
            f"opinion, announcement, documentation, comparison, other\n"
            f"2. tags — 3-6 short topic tags (technologies, concepts, patterns)\n\n"
            f"Respond with valid JSON: {{\"content_type\": \"...\", \"tags\": [...]}}"
        ),
        expected_output='JSON with content_type (string) and tags (list of strings)',
        agent=classifier,
    )

    analyze_task = Task(
        description=(
            f"Read this article and evaluate its technical merits:\n\n"
            f"Title: {article_title}\n\n"
            f"Text:\n{article_text[:6000]}\n\n"
            f"Previous classification: {{{{classify_task.output}}}}\n\n"
            f"Determine:\n"
            f"1. technical_depth (0-10) — is there architecture, code, real implementation?\n"
            f"2. has_code_examples (true/false) — runnable code, configs, commands?\n"
            f"3. has_performance_data (true/false) — latency, throughput, $ cost cited?\n"
            f"4. practical_value (0-10) — can a reader implement what they learn?\n\n"
            f"Respond with valid JSON."
        ),
        expected_output=(
            'JSON with technical_depth (0-10 int), has_code_examples (bool), '
            'has_performance_data (bool), practical_value (0-10 int)'
        ),
        agent=analyst,
        context=[classify_task],
    )

    judge_task = Task(
        description=(
            f"Read this article and judge its authenticity:\n\n"
            f"Title: {article_title}\n\n"
            f"Text:\n{article_text[:6000]}\n\n"
            f"Previous classification: {{{{classify_task.output}}}}\n"
            f"Previous analysis: {{{{analyze_task.output}}}}\n\n"
            f"Determine:\n"
            f"1. marketing_bias (0-10) — is this selling or teaching?\n"
            f"2. originality (0-10) — novel insight or rehash?\n"
            f"3. is_practitioner (true/false) — does author sound like a hands-on engineer?\n\n"
            f"Respond with valid JSON."
        ),
        expected_output=(
            'JSON with marketing_bias (0-10 int), originality (0-10 int), '
            'is_practitioner (bool)'
        ),
        agent=judge,
        context=[classify_task, analyze_task],
    )

    synthesize_task = Task(
        description=(
            f"Review this article and all evaluation signals to produce a final verdict:\n\n"
            f"Title: {article_title}\n\n"
            f"Text:\n{article_text[:6000]}\n\n"
            f"Classification: {{{{classify_task.output}}}}\n"
            f"Technical analysis: {{{{analyze_task.output}}}}\n"
            f"Authenticity judgment: {{{{judge_task.output}}}}\n\n"
            f"Produce:\n"
            f"1. overall_score (0.0-1.0) — composite weighted heavily on technical_depth, "
            f"originality, and practical_value, penalized by marketing_bias\n"
            f"2. reasoning — 2-3 sentences explaining the score, tying the dimensions together\n\n"
            f"Respond with valid JSON."
        ),
        expected_output='JSON with overall_score (0.0-1.0 float) and reasoning (string)',
        agent=editor,
        context=[classify_task, analyze_task, judge_task],
    )

    return classify_task, analyze_task, judge_task, synthesize_task


# ── Output Parsing ────────────────────────────────────────────────────

def parse_json_output(raw: str):
    """Extract and parse JSON from a CrewAI task output string."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try to find a JSON block in the text
    import re
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    llm_logger.warning(f"Could not parse JSON from: {raw[:200]}")
    return None


# ── Public API ────────────────────────────────────────────────────────

class EvaluationResult:
    """Structured result from the full agentic evaluation."""
    def __init__(self, data: dict):
        self.content_type = data.get("content_type", "other")
        self.technical_depth = data.get("technical_depth", 0)
        self.marketing_bias = data.get("marketing_bias", 5)
        self.originality = data.get("originality", 0)
        self.practical_value = data.get("practical_value", 0)
        self.has_code_examples = data.get("has_code_examples", False)
        self.has_performance_data = data.get("has_performance_data", False)
        self.is_practitioner = data.get("is_practitioner", False)
        self.overall_score = data.get("overall_score", 0.0)
        self.reasoning = data.get("reasoning", "")
        self.tags = data.get("tags", [])

    def to_dict(self):
        return {
            "content_type": self.content_type,
            "technical_depth": self.technical_depth,
            "marketing_bias": self.marketing_bias,
            "originality": self.originality,
            "practical_value": self.practical_value,
            "has_code_examples": self.has_code_examples,
            "has_performance_data": self.has_performance_data,
            "is_practitioner": self.is_practitioner,
            "overall_score": self.overall_score,
            "reasoning": self.reasoning,
            "tags": self.tags,
        }

    def __repr__(self):
        return (
            f"EvaluationResult(type={self.content_type}, "
            f"depth={self.technical_depth}/10, mktg={self.marketing_bias}/10, "
            f"orig={self.originality}/10, value={self.practical_value}/10, "
            f"score={self.overall_score:.2f})"
        )


def run_evaluation(title: str, text: str) -> Optional[EvaluationResult]:
    """Run the full 4-agent CrewAI evaluation on an article.

    Args:
        title: Article title.
        text: Full article text content.

    Returns:
        EvaluationResult with all dimensions, or None if evaluation fails.
    """
    if not text or len(text) < 300:
        llm_logger.warning(f"Article too short ({len(text) if text else 0} chars) — skipping")
        return None
    if not DEEPSEEK_API_KEY:
        llm_logger.warning("DEEPSEEK_API_KEY not set")
        return None

    truncated = text[:6000]
    llm_logger.info(f"Starting CrewAI evaluation: {title[:60]}... ({len(truncated)} chars)")

    llm = create_llm()
    agents = create_agents(llm)
    tasks = create_tasks(agents, truncated, title)

    from crewai import Crew, Process
    crew = Crew(
        agents=list(agents),
        tasks=list(tasks),
        process=Process.sequential,
        verbose=True,
    )

    try:
        result = crew.kickoff()

        # Parse each task's output
        classify_out = parse_json_output(tasks[0].output.raw if tasks[0].output else "{}") or {}
        analyze_out = parse_json_output(tasks[1].output.raw if tasks[1].output else "{}") or {}
        judge_out = parse_json_output(tasks[2].output.raw if tasks[2].output else "{}") or {}
        synthesize_out = parse_json_output(tasks[3].output.raw if tasks[3].output else "{}") or {}

        merged = {
            **classify_out,
            **analyze_out,
            **judge_out,
            **synthesize_out,
        }

        eval_result = EvaluationResult(merged)
        llm_logger.info(
            f"Evaluation complete: type={eval_result.content_type}, "
            f"depth={eval_result.technical_depth}/10, "
            f"marketing={eval_result.marketing_bias}/10, "
            f"overall={eval_result.overall_score:.2f}"
        )
        return eval_result

    except Exception as e:
        llm_logger.error(f"CrewAI evaluation failed: {e}", exc_info=True)
        return None


# ── Database helpers ──────────────────────────────────────────────────

def save_evaluation(article_id: int, result: EvaluationResult) -> bool:
    """Persist an evaluation result to the article_evaluations table."""
    from storage.database import get_db_conn

    conn = get_db_conn()
    if not conn:
        return False

    try:
        tags_json = json.dumps(result.tags)
        conn.execute("""
            INSERT OR REPLACE INTO article_evaluations
            (article_id, content_type, technical_depth, marketing_bias,
             originality, practical_value, has_code_examples,
             has_performance_data, is_practitioner, overall_score,
             reasoning, tags_json, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article_id,
            result.content_type,
            result.technical_depth,
            result.marketing_bias,
            result.originality,
            result.practical_value,
            1 if result.has_code_examples else 0,
            1 if result.has_performance_data else 0,
            1 if result.is_practitioner else 0,
            result.overall_score,
            result.reasoning,
            tags_json,
            json.dumps(result.to_dict()),
        ))
        conn.commit()
        llm_logger.info(f"Saved evaluation for article {article_id}")
        return True
    except Exception as e:
        llm_logger.error(f"Failed to save evaluation: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def get_evaluation(article_id: int) -> Optional[dict]:
    """Fetch a saved evaluation for an article."""
    from storage.database import get_db_conn

    conn = get_db_conn()
    if not conn:
        return None

    try:
        row = conn.execute(
            "SELECT * FROM article_evaluations WHERE article_id = ?",
            (article_id,)
        ).fetchone()
        if not row:
            return None
        return dict(row)
    except Exception:
        return None
    finally:
        conn.close()


def list_evaluations(limit: int = 50, offset: int = 0,
                     min_score: Optional[float] = None,
                     content_type: Optional[str] = None,
                     min_depth: Optional[int] = None,
                     has_code: Optional[bool] = None,
                     sort_by: str = "overall_score") -> list[dict]:
    """Query evaluations with optional filters, joined with article metadata."""
    from storage.database import get_db_conn

    conn = get_db_conn()
    if not conn:
        return []

    try:
        clauses = []
        params = []

        if min_score is not None:
            clauses.append("e.overall_score >= ?")
            params.append(min_score)
        if content_type:
            clauses.append("e.content_type = ?")
            params.append(content_type)
        if min_depth is not None:
            clauses.append("e.technical_depth >= ?")
            params.append(min_depth)
        if has_code is not None:
            clauses.append("e.has_code_examples = ?")
            params.append(1 if has_code else 0)

        where = " AND ".join(clauses) if clauses else "1=1"
        allowed_sort = {"overall_score", "technical_depth", "originality",
                        "practical_value", "marketing_bias", "created_at"}
        order_col = sort_by if sort_by in allowed_sort else "overall_score"

        rows = conn.execute(f"""
            SELECT e.*, a.title, a.blog_name, a.url, a.combined_score AS existing_score
            FROM article_evaluations e
            LEFT JOIN articles a ON a.rowid = e.article_id
            WHERE {where}
            ORDER BY e.{order_col} DESC
            LIMIT ? OFFSET ?
        """, (*params, limit, offset)).fetchall()

        return [dict(r) for r in rows]
    except Exception as e:
        llm_logger.error(f"Failed to list evaluations: {e}")
        return []
    finally:
        conn.close()
