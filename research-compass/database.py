"""Database models and setup for Research Compass."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///research_compass.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    arxiv_id = Column(String, unique=True, nullable=True)
    semantic_id = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=False)
    abstract = Column(Text)
    authors = Column(Text)  # JSON string of author list
    source = Column(String)  # "arxiv" or "semantic_scholar"
    pub_date = Column(String)
    url = Column(String)
    query = Column(String)  # which standing query found this
    created_at = Column(DateTime, default=utcnow)


class RelevanceScore(Base):
    __tablename__ = "relevance_scores"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, nullable=False)
    synthetic_research_score = Column(Float, default=0.0)
    micora_score = Column(Float, default=0.0)
    strategic_growth_score = Column(Float, default=0.0)
    thought_leadership_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    hook = Column(Text)
    linkedin_angle = Column(Text)
    client_application = Column(Text)
    methodology_connection = Column(String)
    created_at = Column(DateTime, default=utcnow)


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # saved, dismissed, team_share, linkedin_draft
    timestamp = Column(DateTime, default=utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    last_visit = Column(DateTime, default=utcnow)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
