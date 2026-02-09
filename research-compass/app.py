"""Research Compass - FastAPI backend for academic paper discovery and scoring."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import STANDING_QUERIES
from database import (
    Paper,
    RelevanceScore,
    UserInteraction,
    UserSession,
    get_db,
    init_db,
)
from scoring import generate_linkedin_post, score_paper
from search import search_all_queries

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Research Compass", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# Track fetch status in memory
fetch_status = {"running": False, "progress": "", "total": 0, "scored": 0}


class InteractionRequest(BaseModel):
    paper_id: int
    action: str


# --- Pages ---


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- API Endpoints ---


@app.get("/api/papers")
def get_papers(db: Session = Depends(get_db)):
    """Get all papers with scores, ordered by overall score descending."""
    results = (
        db.query(Paper, RelevanceScore)
        .outerjoin(RelevanceScore, Paper.id == RelevanceScore.paper_id)
        .order_by(RelevanceScore.overall_score.desc().nullslast())
        .all()
    )

    # Get dismissed paper IDs
    dismissed = {
        row.paper_id
        for row in db.query(UserInteraction)
        .filter(UserInteraction.action == "dismissed")
        .all()
    }

    papers = []
    for paper, score in results:
        if paper.id in dismissed:
            continue

        authors = []
        try:
            authors = json.loads(paper.authors) if paper.authors else []
        except (json.JSONDecodeError, TypeError):
            authors = [paper.authors] if paper.authors else []

        # Get interactions for this paper
        interactions = (
            db.query(UserInteraction)
            .filter(UserInteraction.paper_id == paper.id)
            .all()
        )
        actions = [i.action for i in interactions]

        paper_data = {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract or "",
            "authors": authors,
            "source": paper.source,
            "pub_date": paper.pub_date,
            "url": paper.url,
            "query": paper.query,
            "actions": actions,
            "scores": None,
        }

        if score:
            paper_data["scores"] = {
                "synthetic_research": score.synthetic_research_score,
                "micora": score.micora_score,
                "strategic_growth": score.strategic_growth_score,
                "thought_leadership": score.thought_leadership_score,
                "overall": score.overall_score,
                "hook": score.hook,
                "linkedin_angle": score.linkedin_angle,
                "client_application": score.client_application,
                "methodology_connection": score.methodology_connection,
            }

        papers.append(paper_data)

    return {"papers": papers, "total": len(papers)}


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    total = db.query(Paper).count()
    scored = db.query(RelevanceScore).count()
    high_relevance = (
        db.query(RelevanceScore)
        .filter(RelevanceScore.overall_score >= 7)
        .count()
    )
    saved = (
        db.query(UserInteraction)
        .filter(UserInteraction.action == "saved")
        .count()
    )

    return {
        "total_papers": total,
        "scored_papers": scored,
        "high_relevance": high_relevance,
        "saved": saved,
    }


@app.post("/api/fetch")
async def fetch_papers(background_tasks: BackgroundTasks):
    """Trigger paper fetch and scoring in the background."""
    if fetch_status["running"]:
        return {"status": "already_running", "message": "Fetch already in progress"}

    background_tasks.add_task(run_fetch_and_score)
    return {"status": "started", "message": "Fetching papers..."}


@app.get("/api/fetch-status")
def get_fetch_status():
    """Check progress of background fetch."""
    return fetch_status


@app.post("/api/interact")
def interact(req: InteractionRequest, db: Session = Depends(get_db)):
    """Record a user interaction with a paper."""
    interaction = UserInteraction(
        paper_id=req.paper_id,
        action=req.action,
    )
    db.add(interaction)
    db.commit()
    return {"status": "ok", "action": req.action, "paper_id": req.paper_id}


@app.post("/api/linkedin/{paper_id}")
def generate_linkedin(paper_id: int, db: Session = Depends(get_db)):
    """Generate a LinkedIn post for a paper."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}

    score = db.query(RelevanceScore).filter(RelevanceScore.paper_id == paper_id).first()

    hook = score.hook if score else ""
    angle = score.linkedin_angle if score else ""

    post = generate_linkedin_post(paper.title, paper.abstract or "", hook, angle)

    # Record the interaction
    interaction = UserInteraction(paper_id=paper_id, action="linkedin_draft")
    db.add(interaction)
    db.commit()

    return {"post": post}


@app.post("/api/session")
def update_session(db: Session = Depends(get_db)):
    """Update last visit timestamp."""
    session = db.query(UserSession).first()
    if session:
        session.last_visit = datetime.now(timezone.utc)
    else:
        session = UserSession()
        db.add(session)
    db.commit()
    return {"status": "ok"}


# --- Background Tasks ---


async def run_fetch_and_score():
    """Fetch papers from all sources, store, and score them."""
    from database import SessionLocal

    fetch_status["running"] = True
    fetch_status["progress"] = "Searching academic databases..."
    fetch_status["scored"] = 0

    db = SessionLocal()

    try:
        papers = await search_all_queries(STANDING_QUERIES)
        fetch_status["total"] = len(papers)
        fetch_status["progress"] = f"Found {len(papers)} papers. Scoring..."

        # First pass: filter out papers already in DB
        new_papers = []
        for paper_data in papers:
            existing = None
            if paper_data.get("arxiv_id"):
                existing = (
                    db.query(Paper)
                    .filter(Paper.arxiv_id == paper_data["arxiv_id"])
                    .first()
                )
            if not existing and paper_data.get("semantic_id"):
                existing = (
                    db.query(Paper)
                    .filter(Paper.semantic_id == paper_data["semantic_id"])
                    .first()
                )
            if not existing:
                # Also check by title to catch cross-source duplicates
                existing = (
                    db.query(Paper)
                    .filter(Paper.title == paper_data["title"])
                    .first()
                )
            if not existing:
                new_papers.append(paper_data)

        fetch_status["total"] = len(new_papers)
        fetch_status["progress"] = (
            f"Found {len(papers)} papers ({len(new_papers)} new). Scoring..."
        )

        new_count = 0
        for i, paper_data in enumerate(new_papers):

            # Store paper
            db_paper = Paper(
                arxiv_id=paper_data.get("arxiv_id"),
                semantic_id=paper_data.get("semantic_id"),
                title=paper_data["title"],
                abstract=paper_data["abstract"],
                authors=paper_data["authors"],
                source=paper_data["source"],
                pub_date=paper_data["pub_date"],
                url=paper_data["url"],
                query=paper_data["query"],
            )
            db.add(db_paper)
            db.commit()
            db.refresh(db_paper)

            # Score paper
            authors_display = paper_data["authors"]
            try:
                authors_list = json.loads(paper_data["authors"])
                authors_display = ", ".join(authors_list[:5])
            except (json.JSONDecodeError, TypeError):
                pass

            fetch_status["progress"] = (
                f"Scoring paper {i+1} of {len(new_papers)}: "
                f"{paper_data['title'][:50]}..."
            )

            result = score_paper(
                paper_data["title"], authors_display, paper_data["abstract"]
            )

            # Brief pause between API calls to avoid rate limits
            await asyncio.sleep(1)

            scores = result.get("scores", {})
            db_score = RelevanceScore(
                paper_id=db_paper.id,
                synthetic_research_score=scores.get("synthetic_research", 0),
                micora_score=scores.get("micora", 0),
                strategic_growth_score=scores.get("strategic_growth", 0),
                thought_leadership_score=scores.get("thought_leadership", 0),
                overall_score=result.get("overall_score", 0),
                hook=result.get("hook", ""),
                linkedin_angle=result.get("linkedin_angle", ""),
                client_application=result.get("client_application", ""),
                methodology_connection=result.get("methodology_connection", ""),
            )
            db.add(db_score)
            db.commit()

            new_count += 1
            fetch_status["scored"] = new_count

        fetch_status["progress"] = (
            f"Done! Added and scored {new_count} new papers."
        )

    except Exception as e:
        logger.error(f"Fetch and score failed: {e}")
        fetch_status["progress"] = f"Error: {e}"
    finally:
        db.close()
        fetch_status["running"] = False


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
