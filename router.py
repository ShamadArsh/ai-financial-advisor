def route(question: str):
    """Route a question to the appropriate agents based on keywords."""
    q = question.lower()

    # News/investment keywords — trigger news fetching + sentiment analysis
    news_keywords = [
        # Action words
        "news", "today", "week", "month", "price", "invest", "market",
        "company", "stock", "buy", "sell", "hold", "trade", "trading",
        "good", "bad", "better", "best", "worth", "outlook", "forecast",
        # Company/stock names
        "nvidia", "apple", "tesla", "amazon", "google", "microsoft",
        "meta", "netflix", "amd", "intel", "jpmorgan", "visa", "paypal",
        "disney", "pfizer", "boeing", "alibaba", "walmart", "costco",
        "nike", "starbucks", "uber", "lyft", "coinbase", "palantir",
        # Industries/sectors
        "steel", "oil", "energy", "tech", "technology", "banking", "finance",
        "pharma", "healthcare", "crypto", "bitcoin", "ethereum", "ai",
        "semiconductor", "automotive", "real estate", "renewable", "solar",
        # Market terms
        "bull", "bear", "bullish", "bearish", "up", "down", "rise", "fall",
        "growth", "earnings", "revenue", "profit", "loss", "dividend",
        "ipo", "acquisition", "merger", "quarter", "quarterly",
        # Ticker patterns
        "aapl", "tsla", "amzn", "msft", "nvda", "googl", "meta", "nflx",
        # Question patterns
        "what about", "how about", "compared", "comparison", "vs", "versus",
        "which", "recommend", "should i", "is it",
    ]

    # Theory/knowledge keywords — trigger RAG retrieval
    theory_keywords = [
        "why", "explain", "pe", "p/e", "valuation", "risk", "fundamental",
        "ratio", "dividend", "eps", "earnings per share", "portfolio",
        "diversif", "hedge", "leverage", "margin", "cap", "capm",
        "sharpe", "alpha", "beta", "volatil", "liquidity", "intrinsic",
        "dollar cost", "averag", "index", "etf", "mutual fund",
        "compound", "discount", "present value", "cash flow",
    ]

    wants_news = any(k in q for k in news_keywords)
    wants_theory = any(k in q for k in theory_keywords)

    # If neither matches, default to news (most common user intent)
    if not wants_news and not wants_theory:
        wants_news = True

    return {"news": wants_news, "theory": wants_theory}


if __name__ == "__main__":
    tests = [
        "Should I invest in NVIDIA?",
        "Is NVIDIA a good buy?",
        "What about Tesla?",
        "Should I invest in steel this month?",
        "What is the outlook for tech stocks?",
        "Explain P/E ratio and valuation",
        "Which is better?",
        "Hello, how are you?",
    ]
    for q in tests:
        r = route(q)
        print(f"{q:45s} → news={r['news']}, theory={r['theory']}")
