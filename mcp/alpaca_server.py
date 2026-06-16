import os
import sys
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Paper trading base URLs
TRADING_URL = "https://paper-api.alpaca.markets/v2"
DATA_URL    = "https://data.alpaca.markets/v2"

mcp = FastMCP("Alpaca Paper Trading Server")


def alpaca_headers() -> dict:
    """Return auth headers for Alpaca API."""
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise ValueError("ALPACA_API_KEY or ALPACA_SECRET_KEY not set in .env")
    return {
        "APCA-API-KEY-ID":     ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type":        "application/json",
    }


def alpaca_get(endpoint: str, params: dict = {}) -> dict | list:
    """GET request to Alpaca trading API."""
    url = f"{TRADING_URL}/{endpoint}"
    response = httpx.get(url, headers=alpaca_headers(), params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def alpaca_post(endpoint: str, body: dict = {}) -> dict:
    """POST request to Alpaca trading API."""
    url = f"{TRADING_URL}/{endpoint}"
    response = httpx.post(url, headers=alpaca_headers(), json=body, timeout=10)
    response.raise_for_status()
    return response.json()


def alpaca_delete(endpoint: str) -> dict | str:
    """DELETE request to Alpaca trading API."""
    url = f"{TRADING_URL}/{endpoint}"
    response = httpx.delete(url, headers=alpaca_headers(), timeout=10)
    if response.status_code == 204:
        return "Success"
    response.raise_for_status()
    return response.json()


# ── Tool 1: Get Account Info ──────────────────────────────────────────────────
@mcp.tool()
def get_account() -> str:
    """
    Get your Alpaca paper trading account details.
    Shows buying power, portfolio value, cash, and account status.
    """
    try:
        a = alpaca_get("account")
        return (
            f"�account Paper Trading Account:\n"
            f"  Status:           {a.get('status', 'N/A')}\n"
            f"  Portfolio Value:  ${float(a.get('portfolio_value', 0)):,.2f}\n"
            f"  Cash:             ${float(a.get('cash', 0)):,.2f}\n"
            f"  Buying Power:     ${float(a.get('buying_power', 0)):,.2f}\n"
            f"  Equity:           ${float(a.get('equity', 0)):,.2f}\n"
            f"  Last Equity:      ${float(a.get('last_equity', 0)):,.2f}\n"
            f"  Day P&L:          ${float(a.get('equity', 0)) - float(a.get('last_equity', 0)):,.2f}\n"
            f"  Daytrade Count:   {a.get('daytrade_count', 'N/A')}\n"
            f"  Pattern Day Trader: {a.get('pattern_day_trader', 'N/A')}"
        )
    except Exception as e:
        return f"❌ Error fetching account: {e}"


# ── Tool 2: Place Market Order ────────────────────────────────────────────────
@mcp.tool()
def place_market_order(ticker: str, side: str, qty: float) -> str:
    """
    Place a market order to buy or sell a stock immediately at current price.

    Args:
        ticker: Stock ticker symbol e.g. NVDA, AAPL, TSLA
        side:   'buy' or 'sell'
        qty:    Number of shares (can be fractional e.g. 0.5)
    """
    if side.lower() not in ["buy", "sell"]:
        return "❌ side must be 'buy' or 'sell'"
    try:
        order = alpaca_post("orders", {
            "symbol":        ticker.upper(),
            "qty":           str(qty),
            "side":          side.lower(),
            "type":          "market",
            "time_in_force": "day",
        })
        return (
            f"✅ Market Order Placed:\n"
            f"  Order ID:   {order.get('id', 'N/A')}\n"
            f"  Symbol:     {order.get('symbol', 'N/A')}\n"
            f"  Side:       {order.get('side', 'N/A').upper()}\n"
            f"  Qty:        {order.get('qty', 'N/A')} shares\n"
            f"  Type:       {order.get('type', 'N/A')}\n"
            f"  Status:     {order.get('status', 'N/A')}\n"
            f"  Submitted:  {order.get('submitted_at', 'N/A')}"
        )
    except Exception as e:
        return f"❌ Error placing market order: {e}"


# ── Tool 3: Place Limit Order ─────────────────────────────────────────────────
@mcp.tool()
def place_limit_order(ticker: str, side: str, qty: float, limit_price: float) -> str:
    """
    Place a limit order to buy or sell only at a specific price or better.

    Args:
        ticker:      Stock ticker symbol e.g. NVDA, AAPL, TSLA
        side:        'buy' or 'sell'
        qty:         Number of shares (can be fractional e.g. 0.5)
        limit_price: The maximum price to buy at (or minimum to sell at)
    """
    if side.lower() not in ["buy", "sell"]:
        return "❌ side must be 'buy' or 'sell'"
    try:
        order = alpaca_post("orders", {
            "symbol":        ticker.upper(),
            "qty":           str(qty),
            "side":          side.lower(),
            "type":          "limit",
            "limit_price":   str(limit_price),
            "time_in_force": "gtc",  # Good Till Cancelled
        })
        return (
            f"✅ Limit Order Placed:\n"
            f"  Order ID:    {order.get('id', 'N/A')}\n"
            f"  Symbol:      {order.get('symbol', 'N/A')}\n"
            f"  Side:        {order.get('side', 'N/A').upper()}\n"
            f"  Qty:         {order.get('qty', 'N/A')} shares\n"
            f"  Limit Price: ${limit_price}\n"
            f"  Status:      {order.get('status', 'N/A')}\n"
            f"  Submitted:   {order.get('submitted_at', 'N/A')}"
        )
    except Exception as e:
        return f"❌ Error placing limit order: {e}"


# ── Tool 4: Get All Positions ─────────────────────────────────────────────────
@mcp.tool()
def get_positions() -> str:
    """
    Get all current open positions in your paper trading portfolio.
    Shows quantity, market value, cost basis, and unrealized P&L for each.
    """
    try:
        positions = alpaca_get("positions")
        if not positions:
            return "📭 No open positions currently."
        lines = ["📈 Open Positions:\n"]
        for p in positions:
            unrealized = float(p.get('unrealized_pl', 0))
            emoji = "🟢" if unrealized >= 0 else "🔴"
            lines.append(
                f"  {emoji} {p.get('symbol', 'N/A')}\n"
                f"     Qty:            {p.get('qty', 'N/A')} shares ({p.get('side', 'N/A')})\n"
                f"     Avg Entry:      ${float(p.get('avg_entry_price', 0)):,.2f}\n"
                f"     Current Price:  ${float(p.get('current_price', 0)):,.2f}\n"
                f"     Market Value:   ${float(p.get('market_value', 0)):,.2f}\n"
                f"     Unrealized P&L: ${unrealized:,.2f} ({p.get('unrealized_plpc', 'N/A')}%)\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error fetching positions: {e}"


# ── Tool 5: Get Open Orders ───────────────────────────────────────────────────
@mcp.tool()
def get_open_orders() -> str:
    """
    Get all currently open (pending) orders in your paper trading account.
    """
    try:
        orders = alpaca_get("orders", {"status": "open"})
        if not orders:
            return "📭 No open orders currently."
        lines = ["📋 Open Orders:\n"]
        for o in orders:
            lines.append(
                f"  {o.get('symbol', 'N/A')} — {o.get('side', 'N/A').upper()} {o.get('qty', 'N/A')} shares\n"
                f"     Type:       {o.get('type', 'N/A')}\n"
                f"     Limit:      ${o.get('limit_price', 'N/A')}\n"
                f"     Status:     {o.get('status', 'N/A')}\n"
                f"     Order ID:   {o.get('id', 'N/A')}\n"
                f"     Submitted:  {o.get('submitted_at', 'N/A')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error fetching orders: {e}"


# ── Tool 6: Cancel Order ──────────────────────────────────────────────────────
@mcp.tool()
def cancel_order(order_id: str) -> str:
    """
    Cancel a specific open order by its order ID.

    Args:
        order_id: The order ID to cancel (get this from get_open_orders)
    """
    try:
        alpaca_delete(f"orders/{order_id}")
        return f"✅ Order {order_id} cancelled successfully."
    except Exception as e:
        return f"❌ Error cancelling order {order_id}: {e}"


# ── Tool 7: Cancel All Orders ─────────────────────────────────────────────────
@mcp.tool()
def cancel_all_orders() -> str:
    """
    Cancel ALL open orders in your paper trading account at once.
    """
    try:
        alpaca_delete("orders")
        return "✅ All open orders cancelled successfully."
    except Exception as e:
        return f"❌ Error cancelling all orders: {e}"


# ── Tool 8: Close Position ────────────────────────────────────────────────────
@mcp.tool()
def close_position(ticker: str) -> str:
    """
    Close (liquidate) your entire position in a specific stock immediately.

    Args:
        ticker: Stock ticker symbol to close e.g. NVDA, AAPL, TSLA
    """
    try:
        result = alpaca_delete(f"positions/{ticker.upper()}")
        if isinstance(result, dict):
            return (
                f"✅ Position Closed:\n"
                f"  Symbol:  {result.get('symbol', ticker.upper())}\n"
                f"  Qty:     {result.get('qty', 'N/A')} shares\n"
                f"  Status:  {result.get('status', 'N/A')}"
            )
        return f"✅ Position in {ticker.upper()} closed successfully."
    except Exception as e:
        return f"❌ Error closing position for {ticker}: {e}"


# ── Tool 9: Get Portfolio History ─────────────────────────────────────────────
@mcp.tool()
def get_portfolio_history(period: str = "1W") -> str:
    """
    Get the performance history of your paper trading portfolio.

    Args:
        period: Time period — '1D', '1W', '1M', '3M', '1A'
    """
    try:
        data = alpaca_get("account/portfolio/history", {"period": period, "timeframe": "1D"})
        equity    = data.get("equity", [])
        profit_loss = data.get("profit_loss", [])
        if not equity:
            return "No portfolio history available."
        start_val = equity[0]  if equity  else 0
        end_val   = equity[-1] if equity  else 0
        total_pl  = profit_loss[-1] if profit_loss else 0
        return (
            f"📊 Portfolio History ({period}):\n"
            f"  Start Value:  ${float(start_val):,.2f}\n"
            f"  End Value:    ${float(end_val):,.2f}\n"
            f"  Total P&L:    ${float(total_pl):,.2f}\n"
            f"  Data Points:  {len(equity)} days"
        )
    except Exception as e:
        return f"❌ Error fetching portfolio history: {e}"


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[alpaca_server] Starting Alpaca Paper Trading MCP Server...", file=sys.stderr)
    mcp.run(transport="stdio")