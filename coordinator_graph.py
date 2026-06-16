import logging
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any

from finbert_agent import analyze_sentiment
from rag_agent import retrieve
from news_agent import get_industry_news
from router import route
from llm_merge_gemini import llm_merge_gemini

logger = logging.getLogger("coordinator")


# -------------------------------
# Graph State
# -------------------------------
class GraphState(TypedDict):
    question: str
    industry: str | None
    news_items: List[Dict] | None
    sentiment: Dict | None
    rag_hits: List[Dict] | None
    conversation_history: List[Dict] | None
    final: Dict | None


# -------------------------------
# Nodes
# -------------------------------
def route_node(state: GraphState) -> str:
    """Route the question to the appropriate agent pipeline."""
    q = state["question"]
    routing = route(q)

    industry = state.get("industry")
    if industry:
        return "news_and_rag"

    if routing["news"] and not routing["theory"]:
        return "news_and_sentiment"

    if routing["theory"] and not routing["news"]:
        return "rag_only"

    if routing["theory"] and routing["news"]:
        return "news_and_rag"

    return "rag_only"


import re

# Common stock tickers and company names for extraction
KNOWN_COMPANIES = [
    "nvidia", "apple", "microsoft", "google", "alphabet", "amazon", "tesla",
    "meta", "facebook", "netflix", "jpmorgan", "visa", "bank of america",
    "paypal", "disney", "pfizer", "costco", "intel", "coca cola", "target",
    "nike", "boeing", "alibaba", "walmart", "ge", "general electric",
    "cisco", "verizon", "johnson", "chevron", "palantir", "block",
    "shopify", "starbucks", "sofi", "robinhood", "roblox", "snap",
    "amd", "uber", "fedex", "abbvie", "etsy", "moderna", "lockheed",
    "general motors", "ford", "lucid", "carnival", "delta", "united airlines",
    "american airlines", "tsmc", "sony", "coinbase", "rivian", "riot",
    "steel", "oil", "energy", "tech", "technology", "banking", "finance",
    "pharma", "healthcare", "real estate", "crypto", "bitcoin", "ethereum",
    "semiconductor", "ai", "artificial intelligence", "electric vehicle",
    "renewable", "solar", "gold", "silver",
]


def extract_company_or_industry(question: str) -> str:
    """Extract the most relevant company or industry keyword from a question.

    Falls back to the full question if no known company/industry is found.
    """
    q_lower = question.lower()

    # Try to find a known company/industry in the question
    found = []
    for company in KNOWN_COMPANIES:
        if company in q_lower:
            found.append(company)

    if found:
        # Return the longest match (most specific)
        return max(found, key=len).upper()

    # Try to find capitalized words that might be a company name
    # e.g., "Should I buy NVDA?" → "NVDA"
    ticker_pattern = r'\b([A-Z]{2,5})\b'
    tickers = re.findall(ticker_pattern, question)
    if tickers:
        return tickers[0]

    # Fallback: remove common question words and use the rest
    stop_words = {
        "should", "i", "invest", "in", "buy", "sell", "the", "a", "an",
        "is", "are", "good", "bad", "this", "month", "year", "now",
        "today", "what", "why", "how", "tell", "me", "about", "stock",
        "stocks", "share", "shares", "company", "market", "price",
        "worth", "hold", "long", "term", "short", "for", "to", "of",
    }
    words = question.lower().split()
    meaningful = [w.strip("?,.!") for w in words if w.strip("?,.!") not in stop_words]
    if meaningful:
        return " ".join(meaningful[:3])  # Use up to 3 meaningful words

    return question


def news_and_sentiment_node(state: GraphState):
    """Fetch news + analyze sentiment."""
    q = state["question"]
    industry = state.get("industry") or extract_company_or_industry(q)

    news = get_industry_news(industry, max_items=8)
    combined = "\n".join([(n.get("content") or n.get("title") or "") for n in news])
    sentiment = analyze_sentiment(combined)

    return {"news_items": news, "sentiment": sentiment}


def rag_only_node(state: GraphState):
    """Retrieve from RAG knowledge base."""
    q = state["question"]
    hits = retrieve(q)
    return {"rag_hits": hits}


def news_and_rag_node(state: GraphState):
    """Fetch news + analyze sentiment + retrieve from RAG."""
    q = state["question"]
    industry = state.get("industry") or extract_company_or_industry(q)

    news = get_industry_news(industry, max_items=8)
    combined = "\n".join([(n.get("content") or n.get("title") or "") for n in news])
    sentiment = analyze_sentiment(combined)
    hits = retrieve(q)

    return {"news_items": news, "sentiment": sentiment, "rag_hits": hits}


def merge_node(state: GraphState):
    """Merge all agent outputs into a final recommendation via Gemini."""
    q = state["question"]
    news = state.get("news_items") or []
    sentiment = state.get("sentiment") or {}
    rag_hits = state.get("rag_hits") or []
    history = state.get("conversation_history") or []

    try:
        answer = llm_merge_gemini(q, sentiment, news, rag_hits, history)
    except Exception as e:
        logger.error("Gemini merge failed: %s", e)
        answer = (
            f"Q: {q}\n"
            f"Sentiment score: {sentiment.get('article_score')}\n"
            f"News: {[n.get('title') for n in news[:3]]}"
        )

    final = {
        "question": q,
        "answer": answer,
        "sentiment": sentiment,
        "news_items": news,
        "rag_hits": rag_hits,
    }

    return {"final": final}


# -------------------------------
# Build Graph
# -------------------------------
workflow = StateGraph(GraphState)

workflow.add_node("news_and_sentiment", news_and_sentiment_node)
workflow.add_node("rag_only", rag_only_node)
workflow.add_node("news_and_rag", news_and_rag_node)
workflow.add_node("merge", merge_node)

workflow.add_conditional_edges(
    START,
    route_node,
    {
        "news_and_sentiment": "news_and_sentiment",
        "rag_only": "rag_only",
        "news_and_rag": "news_and_rag",
    },
)

workflow.add_edge("news_and_sentiment", "merge")
workflow.add_edge("rag_only", "merge")
workflow.add_edge("news_and_rag", "merge")
workflow.add_edge("merge", END)

app_graph = workflow.compile()


def run_advisor(
    question: str,
    industry: str | None = None,
    conversation_history: list | None = None,
) -> dict:
    """Synchronous wrapper to run the advisor graph.

    Args:
        question: The user's question.
        industry: Optional industry/company override.
        conversation_history: List of past {"role","content"} messages for context.

    Returns the 'final' dict with: question, answer, sentiment, news_items, rag_hits.
    """
    logger.info("Running advisor for question='%s' industry='%s' history_len=%d",
                question, industry, len(conversation_history or []))
    result = app_graph.invoke({
        "question": question,
        "industry": industry,
        "conversation_history": conversation_history or [],
    })
    return result.get("final", {})


if __name__ == "__main__":
    from pprint import pprint

    final_state = run_advisor("Should I invest in steel this month?", industry="steel")
    pprint(final_state)
