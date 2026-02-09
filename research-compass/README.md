# Research Compass

Academic paper discovery and scoring system for Part and Sum. Searches arXiv and Semantic Scholar, scores papers against your business methodologies using Claude, and generates LinkedIn posts for high-relevance findings.

## Setup

1. **Clone and enter the directory:**
   ```bash
   cd research-compass
   ```

2. **Create your `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your Anthropic API key
   ```

3. **Run with the start script:**
   ```bash
   ./start.sh
   ```

   Or manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```

4. **Open** [http://localhost:8000](http://localhost:8000)

## Usage

1. Click **Fetch New Papers** to search all 8 standing queries across arXiv and Semantic Scholar
2. Papers are scored on 4 dimensions (Synthetic Research, MICORA, Strategic Growth, Thought Leadership)
3. High-relevance papers (7+) get a green border and the **LinkedIn Draft** button
4. Click **LinkedIn Draft** to generate a post in your voice, then copy to clipboard
5. Use **Save**, **Share with Team**, or **Dismiss** to manage your feed

## Configuration

Edit `config.py` to adjust:
- **Standing queries** - topics to monitor
- **Scoring weights** - how much each dimension matters
- **Business context** - your firm's methodologies and focus areas
- **LinkedIn voice** - tone and style for generated posts
- **Search parameters** - days to look back, results per query

## Costs

Each paper scored costs ~$0.01 in Claude API usage. A typical refresh (50-100 papers) runs $0.50-$1.00.

## File Structure

```
research-compass/
├── app.py              # FastAPI server and endpoints
├── config.py           # Queries, weights, business context
├── database.py         # SQLAlchemy models (SQLite)
├── search.py           # arXiv + Semantic Scholar search
├── scoring.py          # Claude API scoring + LinkedIn generation
├── templates/
│   └── index.html      # Frontend interface
├── requirements.txt    # Python dependencies
├── .env.example        # API key template
├── .gitignore          # Ignore .env, db, venv
└── start.sh            # Quick start script
```
