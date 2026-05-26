# Business Idea Radar

Reddit-powered business idea scanner that monitors trending problems and validates opportunities with AI.

## Features

- Scans Reddit for real problems people are willing to pay to solve
- AI-powered validation using Claude API (optional)
- Streamlit dashboard for browsing and filtering results
- JSON + Markdown report generation
- Works fully offline with `--local` mode

## Tech Stack

- **Python** — Core scraping engine
- **PRAW** — Reddit API client
- **Streamlit** — Interactive dashboard
- **Anthropic SDK** — AI validation (optional)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill environment variables
cp .env.example .env

# Run the scanner
python reddit_idea_radar.py

# Launch the dashboard
streamlit run dashboard.py
```

## Configuration

Copy `.env.example` to `.env` and add your API keys:

| Variable | Required | Description |
|----------|----------|-------------|
| `REDDIT_CLIENT_ID` | Yes | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Yes | Reddit app secret |
| `ANTHROPIC_API_KEY` | No | For AI-powered validation |

## License

MIT
