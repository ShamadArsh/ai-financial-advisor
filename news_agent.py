import os
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger("news_agent")

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY_ORG", "").strip()

DEFAULT_DOMAINS = "economictimes.indiatimes.com,moneycontrol.com,bloomberg.com,reuters.com,livemint.com,thestatesman.com"


def build_industry_query(industry: str, extra_terms: list | None = None):
    """Build a NewsAPI boolean query targeting industry + stock/sector terms."""
    industry = industry.strip()
    terms = [industry, f"{industry} industry", f"{industry} stocks", f"{industry} sector"]
    if extra_terms:
        terms += extra_terms
    q = " OR ".join([f'"{t}"' for t in terms])
    q = f"({q}) AND (market OR stock OR earnings OR revenue OR guidance OR 'earnings' OR 'quarter' OR 'shares' OR 'IPO' OR 'acquisition')"
    return q


def fetch_newsapi_industry(industry: str, days_back: int = 7, max_items: int = 20, domains: str = None):
    """Fetch industry news from NewsAPI.org."""
    if not NEWSAPI_KEY:
        logger.warning("No NEWSAPI_KEY_ORG set — skipping NewsAPI")
        return []

    domains = domains or DEFAULT_DOMAINS
    from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    q = build_industry_query(industry)

    params = {
        "q": q,
        "from": from_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": max_items,
        "domains": domains,
        "apiKey": NEWSAPI_KEY,
    }
    try:
        r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=12)
        data = r.json()
        if data.get("status") != "ok":
            logger.error("NewsAPI error: %s", data)
            return []

        items = []
        for a in data.get("articles", []):
            content = a.get("content") or a.get("description") or a.get("title") or ""
            items.append(
                {
                    "title": a.get("title"),
                    "url": a.get("url"),
                    "content": content,
                    "publishedAt": a.get("publishedAt"),
                    "source": a.get("source", {}).get("name"),
                }
            )
        logger.info("NewsAPI returned %d items for industry='%s'", len(items), industry)
        return items
    except Exception as e:
        logger.error("NewsAPI exception: %s", e)
        return []


def scrape_moneycontrol_filtered(industry: str, max_items: int = 10):
    """Scrape headlines + article content from MoneyControl as fallback."""
    from bs4 import BeautifulSoup

    base = "https://www.moneycontrol.com"
    q = industry.replace(" ", "+")
    search_url = f"https://www.moneycontrol.com/news/search.php?query={q}"
    try:
        r = requests.get(search_url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".search_wrap .newsTitle a")[: max_items * 2]
        results = []
        for a in cards:
            title = a.get_text(strip=True)
            href = a.get("href")
            if not href:
                continue
            if not href.startswith("http"):
                href = base + href
            try:
                art = requests.get(href, timeout=10).text
                art_soup = BeautifulSoup(art, "html.parser")
                paragraphs = [p.get_text(strip=True) for p in art_soup.select(".artText p")]
                content = "\n".join(paragraphs)[:5000]
            except Exception:
                content = ""
            text_blob = (title + " " + (content or "")).lower()
            if industry.lower() in text_blob:
                results.append({"title": title, "url": href, "content": content})
            if len(results) >= max_items:
                break
        logger.info("Scraper returned %d items for industry='%s'", len(results), industry)
        return results
    except Exception as e:
        logger.error("Scraper error: %s", e)
        return []


def get_industry_news(industry: str, max_items: int = 10, days_back: int = 7):
    """Unified news interface: try NewsAPI first, fall back to scraper."""
    items = fetch_newsapi_industry(industry, days_back=days_back, max_items=max_items)
    if items:
        return items
    return scrape_moneycontrol_filtered(industry, max_items=max_items)


if __name__ == "__main__":
    print(get_industry_news("steel", max_items=5))
