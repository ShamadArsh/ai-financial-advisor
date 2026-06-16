import os
import sys
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

mcp = FastMCP("FMP Financial Server")


def fmp_get(endpoint: str, params: dict = {}) -> dict | list:
    if not FMP_API_KEY:
        raise ValueError("FMP_API_KEY not set in .env")
    params["apikey"] = FMP_API_KEY
    url = f"{FMP_BASE_URL}/{endpoint}"
    response = httpx.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_stock_quote(ticker: str) -> str:
    """Get live stock quote: price, change, volume, market cap, P/E, EPS. Args: ticker e.g. NVDA"""
    try:
        data = fmp_get(f"quote/{ticker.upper()}")
        if not data:
            return f"No quote found for {ticker}."
        q = data[0]
        return (
            f"Live Quote - {ticker.upper()}:\n"
            f"  Price: ${q.get('price','N/A')} | Change: {q.get('change','N/A')} ({q.get('changesPercentage','N/A')}%)\n"
            f"  Day High/Low: ${q.get('dayHigh','N/A')} / ${q.get('dayLow','N/A')}\n"
            f"  52w High/Low: ${q.get('yearHigh','N/A')} / ${q.get('yearLow','N/A')}\n"
            f"  Volume: {q.get('volume',0):,} | Avg Volume: {q.get('avgVolume',0):,}\n"
            f"  Market Cap: ${q.get('marketCap',0):,}\n"
            f"  P/E: {q.get('pe','N/A')} | EPS: {q.get('eps','N/A')}\n"
            f"  50D Avg: ${q.get('priceAvg50','N/A')} | 200D Avg: ${q.get('priceAvg200','N/A')}\n"
            f"  Open: ${q.get('open','N/A')} | Prev Close: ${q.get('previousClose','N/A')}"
        )
    except Exception as e:
        return f"Error fetching quote for {ticker}: {e}"


@mcp.tool()
def get_company_profile(ticker: str) -> str:
    """Get company profile: sector, industry, CEO, employees, description. Args: ticker e.g. NVDA"""
    try:
        data = fmp_get(f"profile/{ticker.upper()}")
        if not data:
            return f"No profile found for {ticker}."
        p = data[0]
        return (
            f"Company Profile - {ticker.upper()}:\n"
            f"  Name: {p.get('companyName','N/A')}\n"
            f"  Sector: {p.get('sector','N/A')} | Industry: {p.get('industry','N/A')}\n"
            f"  Exchange: {p.get('exchangeShortName','N/A')} | Country: {p.get('country','N/A')}\n"
            f"  Market Cap: ${p.get('mktCap',0):,} | Beta: {p.get('beta','N/A')}\n"
            f"  CEO: {p.get('ceo','N/A')} | Employees: {p.get('fullTimeEmployees','N/A')}\n"
            f"  IPO Date: {p.get('ipoDate','N/A')} | Website: {p.get('website','N/A')}\n"
            f"  Description: {str(p.get('description','N/A'))[:400]}..."
        )
    except Exception as e:
        return f"Error fetching profile for {ticker}: {e}"


@mcp.tool()
def get_income_statement(ticker: str, period: str = "annual") -> str:
    """Get income statement: revenue, net income, EBITDA. Args: ticker e.g. NVDA, period: annual or quarter"""
    try:
        data = fmp_get(f"income-statement/{ticker.upper()}", {"period": period, "limit": 1})
        if not data:
            return f"No income statement found for {ticker}."
        i = data[0]
        return (
            f"Income Statement - {ticker.upper()} ({period}) {i.get('date','N/A')}:\n"
            f"  Revenue:          ${i.get('revenue',0):,}\n"
            f"  Gross Profit:     ${i.get('grossProfit',0):,} ({round(i.get('grossProfitRatio',0)*100,2)}%)\n"
            f"  R&D:              ${i.get('researchAndDevelopmentExpenses',0):,}\n"
            f"  Operating Income: ${i.get('operatingIncome',0):,}\n"
            f"  EBITDA:           ${i.get('ebitda',0):,}\n"
            f"  Net Income:       ${i.get('netIncome',0):,} ({round(i.get('netIncomeRatio',0)*100,2)}%)\n"
            f"  EPS:              {i.get('eps','N/A')} | EPS Diluted: {i.get('epsdiluted','N/A')}"
        )
    except Exception as e:
        return f"Error fetching income statement for {ticker}: {e}"


@mcp.tool()
def get_balance_sheet(ticker: str, period: str = "annual") -> str:
    """Get balance sheet: assets, liabilities, equity, cash, debt. Args: ticker e.g. NVDA, period: annual or quarter"""
    try:
        data = fmp_get(f"balance-sheet-statement/{ticker.upper()}", {"period": period, "limit": 1})
        if not data:
            return f"No balance sheet found for {ticker}."
        b = data[0]
        return (
            f"Balance Sheet - {ticker.upper()} ({period}) {b.get('date','N/A')}:\n"
            f"  Cash & Equivalents:   ${b.get('cashAndCashEquivalents',0):,}\n"
            f"  Total Current Assets: ${b.get('totalCurrentAssets',0):,}\n"
            f"  Total Assets:         ${b.get('totalAssets',0):,}\n"
            f"  Total Current Liab:   ${b.get('totalCurrentLiabilities',0):,}\n"
            f"  Long Term Debt:       ${b.get('longTermDebt',0):,}\n"
            f"  Total Liabilities:    ${b.get('totalLiabilities',0):,}\n"
            f"  Total Equity:         ${b.get('totalStockholdersEquity',0):,}\n"
            f"  Retained Earnings:    ${b.get('retainedEarnings',0):,}"
        )
    except Exception as e:
        return f"Error fetching balance sheet for {ticker}: {e}"


@mcp.tool()
def get_cash_flow(ticker: str, period: str = "annual") -> str:
    """Get cash flow statement: operating, investing, financing, free cash flow. Args: ticker e.g. NVDA, period: annual or quarter"""
    try:
        data = fmp_get(f"cash-flow-statement/{ticker.upper()}", {"period": period, "limit": 1})
        if not data:
            return f"No cash flow data found for {ticker}."
        c = data[0]
        return (
            f"Cash Flow - {ticker.upper()} ({period}) {c.get('date','N/A')}:\n"
            f"  Operating Cash Flow:  ${c.get('operatingCashFlow',0):,}\n"
            f"  Capital Expenditure:  ${c.get('capitalExpenditure',0):,}\n"
            f"  Free Cash Flow:       ${c.get('freeCashFlow',0):,}\n"
            f"  Investing Cash Flow:  ${c.get('netCashUsedForInvestingActivities',0):,}\n"
            f"  Financing Cash Flow:  ${c.get('netCashUsedProvidedByFinancingActivities',0):,}\n"
            f"  Dividends Paid:       ${c.get('dividendsPaid',0):,}\n"
            f"  Stock Repurchases:    ${c.get('commonStockRepurchased',0):,}\n"
            f"  Net Change in Cash:   ${c.get('netChangeInCash',0):,}"
        )
    except Exception as e:
        return f"Error fetching cash flow for {ticker}: {e}"


@mcp.tool()
def get_stock_news(ticker: str, limit: int = 5) -> str:
    """Get latest news articles for a stock. Args: ticker e.g. NVDA, limit: number of articles (max 10)"""
    try:
        data = fmp_get("stock_news", {"tickers": ticker.upper(), "limit": min(limit, 10)})
        if not data:
            return f"No news found for {ticker}."
        lines = [f"Latest News - {ticker.upper()}:\n"]
        for idx, a in enumerate(data, 1):
            lines.append(
                f"  {idx}. {a.get('title','N/A')}\n"
                f"     Source: {a.get('site','N/A')} | {a.get('publishedDate','N/A')}\n"
                f"     URL: {a.get('url','N/A')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching news for {ticker}: {e}"


@mcp.tool()
def search_ticker(query: str, limit: int = 5) -> str:
    """Search for a stock ticker by company name or partial symbol. Args: query e.g. 'nvidia' or 'NVDA'"""
    try:
        data = fmp_get("search", {"query": query, "limit": limit})
        if not data:
            return f"No results found for '{query}'."
        lines = [f"Search Results for '{query}':\n"]
        for r in data:
            lines.append(
                f"  {r.get('symbol','N/A')} - {r.get('name','N/A')} "
                f"({r.get('exchangeShortName','N/A')} | {r.get('currency','N/A')})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching for '{query}': {e}"


@mcp.tool()
def get_historical_price(ticker: str, from_date: str, to_date: str) -> str:
    """Get historical daily prices for a stock. Args: ticker e.g. NVDA, from_date: YYYY-MM-DD, to_date: YYYY-MM-DD"""
    try:
        data = fmp_get(f"historical-price-full/{ticker.upper()}", {"from": from_date, "to": to_date})
        history = data.get("historical", [])
        if not history:
            return f"No historical data found for {ticker} from {from_date} to {to_date}."
        lines = [f"Historical Prices - {ticker.upper()} ({from_date} to {to_date}):\n"]
        for h in history[:10]:
            lines.append(
                f"  {h.get('date','N/A')}  "
                f"Open: ${h.get('open','N/A')}  Close: ${h.get('close','N/A')}  "
                f"High: ${h.get('high','N/A')}  Low: ${h.get('low','N/A')}  "
                f"Vol: {h.get('volume',0):,}"
            )
        if len(history) > 10:
            lines.append(f"\n  ...and {len(history) - 10} more trading days.")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching historical prices for {ticker}: {e}"


if __name__ == "__main__":
    print("[fmp_server] Starting FMP MCP Server via stdio...", file=sys.stderr)
    mcp.run(transport="stdio")