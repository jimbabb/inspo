"""Configuration for Research Compass - Part and Sum paper discovery system."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Search Configuration
DAYS_LOOKBACK = 30
MAX_RESULTS_PER_QUERY = 20

# Standing Queries - Topics to monitor
STANDING_QUERIES = [
    "synthetic data generation validation research",
    "AI creative generation evaluation",
    "human AI collaboration frameworks",
    "behavioral science marketing effectiveness",
    "creative testing A/B experimentation",
    "brand attribution measurement",
    "LLM bias mitigation evaluation",
    "cross-disciplinary innovation frameworks",
]

# Scoring Weights
SCORING_WEIGHTS = {
    "synthetic_research": 0.30,
    "micora": 0.25,
    "strategic_growth": 0.25,
    "thought_leadership": 0.20,
}

# Part and Sum Business Context (used in Claude scoring prompts)
BUSINESS_CONTEXT = """
Part and Sum is a strategy firm that specializes in:

## 1. Synthetic Research Methodology
- Hybrid human+AI research approach
- Human qualitative interviews create foundation
- AI synthetic personas scale insights rapidly
- Continuous validation loop between human and machine
- Philosophy: "AI should make research more human, not less"

## 2. MICORA Platform
- AI-powered creative production at scale
- Trained on client brand systems
- Generates channel-specific content (Meta, YouTube, TikTok, email)
- Creative director-led to ensure quality
- Rapid iteration cycles (2-3 weeks)

## 3. Client Challenges We Solve
- Moving from performance to brand investment (proving ROI)
- Understanding customer engagement today (what/where/how to communicate)
- Validating creative work before launch
- Proving business value of marketing
- Automating grunt work to focus on strategic thinking
- Finding inspiration and staying current
"""

SCORING_CRITERIA = {
    "synthetic_research": (
        "Synthetic Research Validation (30% weight): "
        "Does this validate or challenge Part and Sum's hybrid human+AI methodology? "
        "Insights on synthetic persona generation? Human-AI collaboration best practices?"
    ),
    "micora": (
        "MICORA Enhancement (25% weight): "
        "Could this improve AI creative production? Creative testing methodology advances? "
        "Brand system codification insights?"
    ),
    "strategic_growth": (
        "Strategic Growth Application (25% weight): "
        "Is this actionable for client work? Does it address client challenges like "
        "brand vs performance ROI, customer engagement, creative validation, marketing value proof? "
        "Provides usable frameworks?"
    ),
    "thought_leadership": (
        "Thought Leadership Potential (20% weight): "
        "Counterintuitive findings? Challenges conventional marketing/business thinking? "
        "Cross-disciplinary connections?"
    ),
}

LINKEDIN_VOICE = """
Write in this voice based on past LinkedIn posts:
- Direct, punchy opening lines that challenge conventional thinking
- Personal reflections mixed with industry insights
- Short paragraphs, easy to scan
- Ends with actionable takeaways or questions
- Educational first, not promotional
- Uses frameworks and concepts
- Sometimes provocative but always substantive
- Example opening lines: "Research has never been faster, but what if 'faster' isn't the problem?"
  or "We don't have a talent problem. We have a meaning problem."
"""
