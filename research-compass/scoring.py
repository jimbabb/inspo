"""Claude API integration for paper scoring and LinkedIn post generation."""

import json
import logging

import anthropic

from config import (
    ANTHROPIC_API_KEY,
    BUSINESS_CONTEXT,
    CLAUDE_MODEL,
    LINKEDIN_VOICE,
    SCORING_CRITERIA,
    SCORING_WEIGHTS,
)

logger = logging.getLogger(__name__)


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def score_paper(title: str, authors: str, abstract: str) -> dict:
    """Score a paper against Part and Sum relevance dimensions using Claude."""
    criteria_text = "\n".join(
        f"{i+1}. {desc}" for i, desc in enumerate(SCORING_CRITERIA.values())
    )

    prompt = f"""You are analyzing academic papers for Part and Sum, a strategy firm.

{BUSINESS_CONTEXT}

PAPER TO EVALUATE:
Title: {title}
Authors: {authors}
Abstract: {abstract}

EVALUATE THIS PAPER on each dimension (0-10 scale, be honest—most papers score 2-5):

{criteria_text}

RESPOND WITH VALID JSON ONLY (no markdown, no explanation):
{{
  "scores": {{
    "synthetic_research": <number 0-10>,
    "micora": <number 0-10>,
    "strategic_growth": <number 0-10>,
    "thought_leadership": <number 0-10>
  }},
  "hook": "<one sentence why this matters to Part and Sum>",
  "linkedin_angle": "<if overall relevance is high, the counterintuitive insight worth sharing>",
  "client_application": "<if highly relevant, how to apply with clients>",
  "methodology_connection": "<Compass Rose | MICORA | Integrated Growth>"
}}"""

    try:
        client = _get_client()
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()

        # Handle possible markdown code fences
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        result = json.loads(raw)
        scores = result["scores"]

        overall = (
            scores["synthetic_research"] * SCORING_WEIGHTS["synthetic_research"]
            + scores["micora"] * SCORING_WEIGHTS["micora"]
            + scores["strategic_growth"] * SCORING_WEIGHTS["strategic_growth"]
            + scores["thought_leadership"] * SCORING_WEIGHTS["thought_leadership"]
        )
        result["overall_score"] = round(overall, 2)
        return result

    except Exception as e:
        logger.error(f"Scoring failed for '{title}': {e}")
        return {
            "scores": {
                "synthetic_research": 0,
                "micora": 0,
                "strategic_growth": 0,
                "thought_leadership": 0,
            },
            "overall_score": 0,
            "hook": "Scoring unavailable",
            "linkedin_angle": "",
            "client_application": "",
            "methodology_connection": "Integrated Growth",
        }


def generate_linkedin_post(title: str, abstract: str, hook: str, linkedin_angle: str) -> str:
    """Generate a LinkedIn post in Jim's voice for a high-scoring paper."""
    prompt = f"""Write a LinkedIn post about this academic paper for a strategy consultant.

{LINKEDIN_VOICE}

PAPER:
Title: {title}
Abstract: {abstract}

KEY INSIGHT: {hook}
ANGLE: {linkedin_angle}

Write a 150-250 word LinkedIn post. No hashtags. No emojis. End with a question or actionable takeaway.
Return ONLY the post text, nothing else."""

    try:
        client = _get_client()
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.error(f"LinkedIn generation failed: {e}")
        return f"Could not generate post. Key insight: {hook}"
