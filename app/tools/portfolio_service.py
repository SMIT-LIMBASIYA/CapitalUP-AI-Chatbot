"""
Portfolio Holdings and P&L Analytics Service.
"""

from typing import Dict, Any, List
from app.db.connection import get_db_pool

async def get_user_portfolio(user_id: int = 1) -> Dict[str, Any]:
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.symbol, p.quantity, p.average_buy_price,
                   s.company_name, s.sector, s.last_price, s.previous_close
            FROM portfolio_holdings p
            LEFT JOIN stocks s ON p.symbol = s.symbol
            WHERE p.user_id = $1
            ORDER BY (p.quantity * COALESCE(s.last_price, p.average_buy_price)) DESC;
            """,
            user_id
        )

        holdings = []
        total_invested = 0.0
        total_current_value = 0.0
        total_day_pnl = 0.0

        for r in rows:
            qty = r["quantity"]
            avg_price = float(r["average_buy_price"])
            last_price = float(r["last_price"]) if r["last_price"] is not None else avg_price
            prev_close = float(r["previous_close"]) if r["previous_close"] is not None else last_price

            invested_val = round(qty * avg_price, 2)
            current_val = round(qty * last_price, 2)
            unrealized_pnl = round(current_val - invested_val, 2)
            unrealized_pnl_pct = round((unrealized_pnl / invested_val * 100), 2) if invested_val > 0 else 0.0

            day_pnl = round(qty * (last_price - prev_close), 2)
            day_pnl_pct = round(((last_price - prev_close) / prev_close * 100), 2) if prev_close > 0 else 0.0

            total_invested += invested_val
            total_current_value += current_val
            total_day_pnl += day_pnl

            holdings.append({
                "symbol": r["symbol"],
                "company_name": r["company_name"] or r["symbol"],
                "sector": r["sector"] or "Equities",
                "quantity": qty,
                "average_buy_price": avg_price,
                "current_price": last_price,
                "invested_value": invested_val,
                "current_value": current_val,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_percent": unrealized_pnl_pct,
                "day_pnl": day_pnl,
                "day_pnl_percent": day_pnl_pct
            })

        overall_pnl = round(total_current_value - total_invested, 2)
        overall_pnl_pct = round((overall_pnl / total_invested * 100), 2) if total_invested > 0 else 0.0

        return {
            "user_id": user_id,
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current_value, 2),
            "total_unrealized_pnl": overall_pnl,
            "total_unrealized_pnl_percent": overall_pnl_pct,
            "total_day_pnl": round(total_day_pnl, 2),
            "holdings_count": len(holdings),
            "holdings": holdings
        }
