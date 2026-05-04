# import os
# import requests
# from bs4 import BeautifulSoup

# NEWSAPI_KEY = os.getenv("NEWSAPI_KEY_ORG", "").strip()

# # -------------------------------
# # 1. NewsAPI-based fetch (primary)
# # -------------------------------
# def fetch_newsapi(query: str, max_items: int = 10):
#     """Fetch news from NewsAPI.org using the 'everything' endpoint."""
#     if not NEWSAPI_KEY:
#         print("[NewsAPI] No API key detected → skipping NewsAPI")
#         return []

#     url = "https://newsapi.org/v2/everything"
#     params = {
#         "q": query,
#         "language": "en",
#         "sortBy": "publishedAt",
#         "pageSize": max_items,
#         "apiKey": NEWSAPI_KEY,
#     }

#     try:
#         r = requests.get(url, params=params, timeout=10)
#         data = r.json()

#         if data.get("status") != "ok":
#             print("[NewsAPI] Error:", data)
#             return []

#         articles = []
#         for a in data.get("articles", []):
#             articles.append({
#                 "title": a.get("title"),
#                 "url":  a.get("url"),
#                 "content": a.get("content") or a.get("description") or "",
#                 "publishedAt": a.get("publishedAt")
#             })

#         return articles

#     except Exception as e:
#         print("[NewsAPI] Exception:", e)
#         return []


# # -----------------------------------
# # 2. Scraper fallback (MoneyControl)
# # -----------------------------------
# def scrape_moneycontrol(query: str, max_items: int = 10):
#     """Scrape headlines + article bodies from MoneyControl as a fallback."""
#     print("[SCRAPER] Using MoneyControl fallback")

#     base = "https://www.moneycontrol.com"
#     url = f"https://www.moneycontrol.com/news/search.php?query={query.replace(' ', '+')}"

#     try:
#         r = requests.get(url, timeout=10)
#         soup = BeautifulSoup(r.text, "html.parser")
#         cards = soup.select(".search_wrap .newsTitle a")

#         results = []
#         for a in cards[:max_items]:
#             title = a.get_text(strip=True)
#             href = a.get("href")
#             if href and not href.startswith("http"):
#                 href = base + href

#             # fetch article content
#             try:
#                 art_html = requests.get(href, timeout=10).text
#                 art_soup = BeautifulSoup(art_html, "html.parser")
#                 paragraphs = [
#                     p.get_text(strip=True)
#                     for p in art_soup.select(".artText p")
#                 ]
#                 content = "\n".join(paragraphs)
#             except:
#                 content = ""

#             results.append({
#                 "title": title,
#                 "url": href,
#                 "content": content
#             })
#         return results

#     except Exception as e:
#         print("[SCRAPER] Exception:", e)
#         return []


# # ----------------------------------------
# # 3. Unified interface (always call this)
# # ----------------------------------------
# def get_news(query: str, max_items: int = 10):
#     """
#     Unified interface:
#     - Try NewsAPI.org first
#     - If no results, fallback to scraper
#     - Always returns a list of {title, url, content}
#     """
#     results = fetch_newsapi(query, max_items)
#     if results:
#         print(f"[NewsAPI] Returned {len(results)} articles")
#         return results

#     # fallback
#     return scrape_moneycontrol(query, max_items)


# # ----------------------------------------
# # 4. Local test
# # ----------------------------------------
# if __name__ == "__main__":
#     print(get_news("steel industry"))
# news_agent.py
import os, requests, re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY_ORG", "").strip()

# safe defaults
DEFAULT_DOMAINS = "economictimes.indiatimes.com,moneycontrol.com,bloomberg.com,reuters.com,livemint.com,thestatesman.com"

def build_industry_query(industry: str, extra_terms: list | None = None):
    """
    Build a NewsAPI boolean query that targets industry + stock/sector terms.
    """
    industry = industry.strip()
    terms = [industry, f"{industry} industry", f"{industry} stocks", f"{industry} sector"]
    if extra_terms:
        terms += extra_terms
    # combine with OR and require one of finance terms
    q = " OR ".join([f'"{t}"' for t in terms])
    # ensure we prefer finance context
    q = f"({q}) AND (market OR stock OR earnings OR revenue OR guidance OR 'earnings' OR 'quarter' OR 'shares' OR 'IPO' OR 'acquisition')"
    return q

def fetch_newsapi_industry(industry: str, days_back:int=7, max_items:int=20, domains:str=None):
    if not NEWSAPI_KEY:
        print("[NewsAPI] No API key, skipping NewsAPI.")
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
            print("[NewsAPI] Error:", data)
            return []
        items = []
        for a in data.get("articles", []):
            content = a.get("content") or a.get("description") or a.get("title") or ""
            items.append({
                "title": a.get("title"),
                "url": a.get("url"),
                "content": content,
                "publishedAt": a.get("publishedAt"),
                "source": a.get("source", {}).get("name")
            })
        print(f"[NewsAPI] Returned {len(items)} items for industry='{industry}'")
        return items
    except Exception as e:
        print("[NewsAPI] Exception:", e)
        return []

# Simple keyword filter fallback for scraped results
def scrape_moneycontrol_filtered(industry: str, max_items:int=10):
    base = "https://www.moneycontrol.com"
    q = industry.replace(" ", "+")
    search_url = f"https://www.moneycontrol.com/news/search.php?query={q}"
    try:
        r = requests.get(search_url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".search_wrap .newsTitle a")[:max_items*2]
        results=[]
        for a in cards:
            title = a.get_text(strip=True)
            href = a.get("href")
            if not href: continue
            if not href.startswith("http"): href = base + href
            try:
                art = requests.get(href, timeout=10).text
                art_soup = BeautifulSoup(art, "html.parser")
                paragraphs = [p.get_text(strip=True) for p in art_soup.select(".artText p")]
                content = "\n".join(paragraphs)[:5000]
            except:
                content = ""
            # filter by industry keyword presence
            text_blob = (title + " " + (content or "")).lower()
            if industry.lower() in text_blob or any(k in text_blob for k in [industry.lower(), industry.lower()+" stock", industry.lower()+" industry"]):
                results.append({"title": title, "url": href, "content": content})
            if len(results) >= max_items:
                break
        print(f"[Scraper] Returned {len(results)} filtered items for industry='{industry}'")
        return results
    except Exception as e:
        print("[Scraper] Error:", e)
        return []

def get_industry_news(industry: str, max_items:int=10, days_back:int=7):
    items = fetch_newsapi_industry(industry, days_back=days_back, max_items=max_items)
    if items:
        return items
    return scrape_moneycontrol_filtered(industry, max_items=max_items)

if __name__ == "__main__":
    print(get_industry_news("steel", max_items=5))
