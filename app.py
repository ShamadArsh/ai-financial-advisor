"""
Financial AI Advisor — FastAPI Web Server
==========================================
Exposes the multi-agent financial advisor (News + RAG + FinBERT + Gemini)
and MCP tools (FMP stock data, Alpaca paper trading) as HTTP endpoints.

Endpoints:
  GET  /              → Chat UI
  POST /api/ask       → Ask a financial question
  GET  /api/health    → Health check + agent status
  GET  /api/agents    → Detailed agent info
  GET  /api/stock/{ticker}  → Live stock quote via FMP MCP
"""

import os
import sys
import logging
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Optional
from collections import defaultdict

# Load .env file at the very start (before any other imports that read env vars)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("app")


# -------------------------------
# In-memory conversation store
# -------------------------------
# Keyed by session_id. Each session stores a list of {"role","content"} dicts.
MAX_HISTORY = 20  # Keep last 20 messages per session
_conversations: dict[str, list[dict]] = defaultdict(list)


def get_history(session_id: str) -> list[dict]:
    """Return the conversation history for a session."""
    return _conversations.get(session_id, [])


def append_history(session_id: str, role: str, content: str):
    """Append a message to the session's history."""
    _conversations[session_id].append({"role": role, "content": content})
    # Trim old messages
    if len(_conversations[session_id]) > MAX_HISTORY:
        _conversations[session_id] = _conversations[session_id][-MAX_HISTORY:]


# -------------------------------
# Lifespan: startup tasks
# -------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Financial AI Advisor ...")
    # Ensure RAG corpus is indexed (lazy — only runs once)
    try:
        from rag_agent import ensure_indexed
        ensure_indexed()
        logger.info("RAG corpus indexed")
    except Exception as e:
        logger.warning("RAG indexing skipped: %s", e)
    yield
    logger.info("Shutting down ...")


# -------------------------------
# App
# -------------------------------
app = FastAPI(
    title="Financial AI Advisor",
    description="Multi-agent AI financial advisor with News, RAG, FinBERT sentiment, and MCP tools.",
    version="1.0.0",
    lifespan=lifespan,
)


# -------------------------------
# Request / Response Models
# -------------------------------
class AskRequest(BaseModel):
    question: str
    industry: Optional[str] = None
    session_id: Optional[str] = None


class AskResponse(BaseModel):
    question: str
    answer: str
    session_id: Optional[str] = None
    sentiment: Optional[dict] = None
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    news_count: int = 0
    rag_hits_count: int = 0
    top_news: list = []
    rag_sources: list = []
    agents_used: list = []
    error: Optional[str] = None


# -------------------------------
# Routes
# -------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the chat UI (no-cache headers to prevent stale UI)."""
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")
    content = open(template_path, "r", encoding="utf-8").read()
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api/health")
async def health():
    """Health check — returns app status and which API keys are configured."""
    return {
        "status": "ok",
        "agents": {
            "news_agent": bool(os.getenv("NEWSAPI_KEY_ORG", "").strip()),
            "rag_agent": True,  # Local model, always available
            "finbert_agent": True,  # Local model, always available
            "gemini_merge": bool(os.getenv("GOOGLE_API_KEY", "").strip()),
            "mcp_fmp": bool(os.getenv("FMP_API_KEY", "").strip()),
            "mcp_alpaca": bool(os.getenv("ALPACA_API_KEY", "").strip() and os.getenv("ALPACA_SECRET_KEY", "").strip()),
            "mcp_groq": bool(os.getenv("GROQ_API_KEY", "").strip()),
        },
    }


@app.get("/api/agents")
async def agents_info():
    """Detailed information about each agent."""
    return {
        "agents": [
            {
                "name": "News Agent",
                "description": "Fetches latest financial news via NewsAPI.org with MoneyControl scraper fallback.",
                "configured": bool(os.getenv("NEWSAPI_KEY_ORG", "").strip()),
                "key_env": "NEWSAPI_KEY_ORG",
            },
            {
                "name": "RAG Agent",
                "description": "Retrieves relevant financial theory from a local ChromaDB knowledge base using SentenceTransformers.",
                "configured": True,
                "key_env": None,
            },
            {
                "name": "FinBERT Agent",
                "description": "Analyzes financial sentiment using the ProsusAI/finbert transformer model.",
                "configured": True,
                "key_env": None,
            },
            {
                "name": "Gemini Merge",
                "description": "Combines all agent outputs into a coherent recommendation using Google Gemini.",
                "configured": bool(os.getenv("GOOGLE_API_KEY", "").strip()),
                "key_env": "GOOGLE_API_KEY",
            },
            {
                "name": "MCP: FMP Server",
                "description": "Provides live stock quotes, company profiles, financials via FinancialModelingPrep.",
                "configured": bool(os.getenv("FMP_API_KEY", "").strip()),
                "key_env": "FMP_API_KEY",
            },
            {
                "name": "MCP: Alpaca Server",
                "description": "Paper trading: place orders, check positions, manage portfolio via Alpaca.",
                "configured": bool(os.getenv("ALPACA_API_KEY", "").strip() and os.getenv("ALPACA_SECRET_KEY", "").strip()),
                "key_env": "ALPACA_API_KEY + ALPACA_SECRET_KEY",
            },
            {
                "name": "MCP: Groq Host",
                "description": "AI trading assistant using Groq (llama-3.3-70b) + Alpaca MCP tools.",
                "configured": bool(os.getenv("GROQ_API_KEY", "").strip()),
                "key_env": "GROQ_API_KEY",
            },
        ]
    }


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """Ask the financial advisor a question.

    Runs the full LangGraph pipeline: route → news/sentiment/rag → Gemini merge.
    Maintains conversation memory across requests via session_id.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    history = get_history(session_id)

    try:
        from coordinator_graph import run_advisor

        # Run the advisor graph with conversation history (CPU-bound → offload to thread)
        result = await asyncio.to_thread(
            run_advisor,
            question=request.question.strip(),
            industry=request.industry,
            conversation_history=history,
        )

        if not result:
            return AskResponse(
                question=request.question,
                answer="No response generated. Please try again.",
                session_id=session_id,
                error="Empty result from advisor graph.",
            )

        # Store this exchange in conversation memory
        answer_text = result.get("answer", "")
        append_history(session_id, "user", request.question.strip())
        append_history(session_id, "assistant", answer_text)

        news = result.get("news_items", []) or []
        top_news = [{"title": n.get("title"), "source": n.get("source"), "url": n.get("url")} for n in news[:5]]

        # Extract RAG source details
        rag_hits = result.get("rag_hits", []) or []
        rag_sources = [
            {
                "text": h.get("text", "")[:200],
                "source": h.get("metadata", {}).get("source", "unknown"),
                "distance": round(h.get("distance", 0), 4),
            }
            for h in rag_hits[:3]
        ]

        # Determine which agents were used
        agents_used = []
        if news:
            agents_used.append("📰 News Agent")
            agents_used.append("🎯 FinBERT Sentiment")
        if rag_hits:
            agents_used.append("📚 RAG Knowledge")
        agents_used.append("🤖 Gemini Merge")

        # Build sentiment summary
        sentiment = result.get("sentiment") or {}
        sentiment_score = sentiment.get("article_score")
        if sentiment_score is not None:
            if sentiment_score > 0.1:
                sentiment_label = "Bullish 📈"
            elif sentiment_score < -0.1:
                sentiment_label = "Bearish 📉"
            else:
                sentiment_label = "Neutral ➡️"
        else:
            sentiment_label = None

        return AskResponse(
            question=result.get("question", request.question),
            answer=result.get("answer", ""),
            session_id=session_id,
            sentiment=sentiment,
            sentiment_label=sentiment_label,
            sentiment_score=sentiment_score,
            news_count=len(news),
            rag_hits_count=len(rag_hits),
            top_news=top_news,
            rag_sources=rag_sources,
            agents_used=agents_used,
        )

    except Exception as e:
        logger.error("Advisor error: %s", e, exc_info=True)
        return AskResponse(
            question=request.question,
            answer="An error occurred while processing your question.",
            session_id=session_id,
            error=str(e),
        )


@app.get("/api/history/{session_id}")
async def get_conversation_history(session_id: str):
    """Get the conversation history for a session."""
    return {"session_id": session_id, "history": get_history(session_id)}


@app.delete("/api/history/{session_id}")
async def clear_conversation_history(session_id: str):
    """Clear the conversation history for a session."""
    if session_id in _conversations:
        del _conversations[session_id]
    return {"session_id": session_id, "status": "cleared"}


@app.get("/api/stock/{ticker}")
async def get_stock_quote(ticker: str):
    """Get a live stock quote via FMP (Financial Modeling Prep)."""
    fmp_key = os.getenv("FMP_API_KEY", "").strip()
    if not fmp_key:
        raise HTTPException(status_code=503, detail="FMP_API_KEY not configured.")

    import httpx

    try:
        url = f"https://financialmodelingprep.com/stable/quote"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params={"symbol": ticker.upper(), "apikey": fmp_key}, timeout=10)
            resp.raise_for_status()
            data = resp.json()

        if not data:
            raise HTTPException(status_code=404, detail=f"No quote found for {ticker}.")

        q = data[0]
        return {
            "ticker": ticker.upper(),
            "price": q.get("price"),
            "change": q.get("change"),
            "change_percent": q.get("changePercentage"),
            "day_high": q.get("dayHigh"),
            "day_low": q.get("dayLow"),
            "year_high": q.get("yearHigh"),
            "year_low": q.get("yearLow"),
            "volume": q.get("volume"),
            "market_cap": q.get("marketCap"),
            "pe_ratio": q.get("pe"),
            "eps": q.get("eps"),
        }
    except httpx.HTTPStatusError as e:
        logger.error("FMP API error for %s: %s", ticker, e)
        raise HTTPException(status_code=502, detail=f"FMP API error: {e}")
    except Exception as e:
        logger.error("Stock quote error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
        workers=1,
    )
