"""Academic paper search module - arXiv and Semantic Scholar integration."""

import asyncio
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import httpx

from config import DAYS_LOOKBACK, MAX_RESULTS_PER_QUERY

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"

# arXiv Atom namespace
ATOM_NS = "{http://www.w3.org/2005/Atom}"


async def search_arxiv(query: str, days_back: int = DAYS_LOOKBACK) -> list[dict]:
    """Search arXiv for recent papers matching query via the Atom API."""
    papers = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Use ti+abs (title + abstract) for more targeted results
            # httpx handles URL encoding, so no need for quote()
            # Wrap multi-word queries in quotes for phrase matching
            # Use all: to search across title, abstract, and all fields
            quoted = f'"{query}"'
            resp = await client.get(
                ARXIV_API,
                params={
                    "search_query": f"all:{quoted}",
                    "start": 0,
                    "max_results": MAX_RESULTS_PER_QUERY,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                },
            )
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        for entry in root.findall(f"{ATOM_NS}entry"):
            title_el = entry.find(f"{ATOM_NS}title")
            summary_el = entry.find(f"{ATOM_NS}summary")
            published_el = entry.find(f"{ATOM_NS}published")
            id_el = entry.find(f"{ATOM_NS}id")

            if title_el is None or summary_el is None:
                continue
            if title_el.text is None or summary_el.text is None:
                continue

            title = " ".join(title_el.text.strip().split())
            abstract = " ".join(summary_el.text.strip().split())

            # Skip the feed-level entries that aren't papers
            if not abstract or len(abstract) < 50:
                continue

            entry_id = id_el.text.strip() if id_el is not None else ""

            # Parse date
            pub_date = None
            if published_el is not None and published_el.text:
                try:
                    pub_date = datetime.fromisoformat(
                        published_el.text.strip().replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            if pub_date and pub_date < cutoff:
                continue

            # Extract authors
            authors = []
            for author_el in entry.findall(f"{ATOM_NS}author"):
                name_el = author_el.find(f"{ATOM_NS}name")
                if name_el is not None and name_el.text:
                    authors.append(name_el.text.strip())

            arxiv_id = entry_id.split("/abs/")[-1] if "/abs/" in entry_id else entry_id

            papers.append({
                "arxiv_id": arxiv_id,
                "semantic_id": None,
                "title": title,
                "abstract": abstract,
                "authors": json.dumps(authors[:10]),
                "source": "arxiv",
                "pub_date": pub_date.strftime("%Y-%m-%d") if pub_date else "",
                "url": entry_id,
                "query": query,
            })

    except Exception as e:
        logger.error(f"arXiv search failed for '{query}': {e}")

    logger.info(f"arXiv '{query}': found {len(papers)} papers")
    return papers


async def search_semantic_scholar(
    query: str, days_back: int = DAYS_LOOKBACK
) -> list[dict]:
    """Search Semantic Scholar for recent papers matching query."""
    papers = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SEMANTIC_SCHOLAR_API}/paper/search",
                params={
                    "query": query,
                    "limit": MAX_RESULTS_PER_QUERY,
                    "fields": "paperId,title,abstract,authors,publicationDate,externalIds,url",
                    "year": f"{datetime.now().year - 1}-",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        for item in data.get("data", []):
            if not item.get("abstract"):
                continue

            # Check date if available, but still include papers with no date
            pub_date_str = item.get("publicationDate")
            skip = False
            if pub_date_str:
                try:
                    pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                    if pub_date < cutoff:
                        skip = True
                except ValueError:
                    pass

            if skip:
                continue

            external_ids = item.get("externalIds") or {}
            arxiv_id = external_ids.get("ArXiv")

            authors = [a.get("name", "") for a in (item.get("authors") or [])[:10]]
            paper_url = item.get("url") or ""
            if arxiv_id:
                paper_url = f"https://arxiv.org/abs/{arxiv_id}"

            papers.append({
                "arxiv_id": arxiv_id,
                "semantic_id": item.get("paperId"),
                "title": item.get("title", "").strip(),
                "abstract": item.get("abstract", "").strip(),
                "authors": json.dumps(authors),
                "source": "semantic_scholar",
                "pub_date": pub_date_str or "",
                "url": paper_url,
                "query": query,
            })

    except Exception as e:
        logger.error(f"Semantic Scholar search failed for '{query}': {e}")

    logger.info(f"Semantic Scholar '{query}': found {len(papers)} papers")
    return papers


def deduplicate_papers(papers: list[dict]) -> list[dict]:
    """Remove duplicate papers based on arXiv ID or title similarity."""
    seen_arxiv_ids = set()
    seen_titles = set()
    unique = []

    for paper in papers:
        arxiv_id = paper.get("arxiv_id")
        title_lower = paper["title"].lower().strip()

        if arxiv_id and arxiv_id in seen_arxiv_ids:
            continue
        if title_lower in seen_titles:
            continue

        if arxiv_id:
            seen_arxiv_ids.add(arxiv_id)
        seen_titles.add(title_lower)
        unique.append(paper)

    return unique


async def search_all_queries(
    queries: list[str], days_back: int = DAYS_LOOKBACK
) -> list[dict]:
    """Search all standing queries across both sources and deduplicate."""
    all_papers = []

    for query in queries:
        arxiv_papers = await search_arxiv(query, days_back)
        # Small delay to respect Semantic Scholar rate limits (100 req / 5 min)
        await asyncio.sleep(1)
        ss_papers = await search_semantic_scholar(query, days_back)
        await asyncio.sleep(1)
        all_papers.extend(arxiv_papers)
        all_papers.extend(ss_papers)
        logger.info(
            f"Query '{query}': {len(arxiv_papers)} arXiv + {len(ss_papers)} SS"
        )

    unique_papers = deduplicate_papers(all_papers)
    logger.info(
        f"Total: {len(all_papers)} raw -> {len(unique_papers)} after dedup"
    )
    return unique_papers
