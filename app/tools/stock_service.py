"""
Stock and Market Data Retrieval Service.
Handles stock lookup, real-time quotes, and market indices from PostgreSQL.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from app.db.connection import get_db_pool

async def get_stock_quote(query: str) -> Optional[Dict[str, Any]]:
    pool = await get_db_pool()
    clean_query = query.strip().upper()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT symbol, company_name, exchange, sector, last_price,
                   day_high, day_low, market_open, previous_close, price_updated_at
            FROM stocks
            WHERE UPPER(symbol) = $1 AND is_active = TRUE;
            """,
            clean_query
        )

        if not row:
            search_pattern = f"%{clean_query}%"
            row = await conn.fetchrow(
                """
                SELECT symbol, company_name, exchange, sector, last_price,
                       day_high, day_low, market_open, previous_close, price_updated_at
                FROM stocks
                WHERE (UPPER(company_name) LIKE $1 OR UPPER(symbol) LIKE $1)
                  AND is_active = TRUE
                ORDER BY
                    CASE WHEN UPPER(symbol) = $2 THEN 1
                         WHEN UPPER(company_name) = $2 THEN 2
                         ELSE 3 END
                LIMIT 1;
                """,
                search_pattern, clean_query
            )

        if not row:
            return None

        last_price = float(row["last_price"]) if row["last_price"] is not None else 0.0
        prev_close = float(row["previous_close"]) if row["previous_close"] is not None else last_price
        change = round(last_price - prev_close, 2)
        change_pct = round((change / prev_close * 100), 2) if prev_close > 0 else 0.0

        return {
            "symbol": row["symbol"],
            "company_name": row["company_name"],
            "exchange": row["exchange"],
            "sector": row["sector"],
            "last_price": last_price,
            "day_high": float(row["day_high"]) if row["day_high"] is not None else last_price,
            "day_low": float(row["day_low"]) if row["day_low"] is not None else last_price,
            "market_open": float(row["market_open"]) if row["market_open"] is not None else last_price,
            "previous_close": prev_close,
            "change": change,
            "change_percent": change_pct,
            "updated_at": row["price_updated_at"].isoformat() if row["price_updated_at"] else None
        }

async def get_all_stocks() -> List[Dict[str, Any]]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT symbol, company_name, sector, last_price, previous_close
            FROM stocks
            WHERE is_active = TRUE
            ORDER BY symbol ASC;
            """
        )
        return [
            {
                "symbol": r["symbol"],
                "company_name": r["company_name"],
                "sector": r["sector"],
                "last_price": float(r["last_price"]) if r["last_price"] else None
            }
            for r in rows
        ]

async def get_market_indices() -> List[Dict[str, Any]]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT symbol, company_name, last_price, previous_close
            FROM stocks
            WHERE symbol IN ('^NSEI', '^BSESN');
            """
        )
        results = []
        for r in rows:
            last = float(r["last_price"]) if r["last_price"] else 0.0
            prev = float(r["previous_close"]) if r["previous_close"] else last
            results.append({
                "symbol": r["symbol"],
                "name": r["company_name"],
                "current_level": last,
                "change": round(last - prev, 2),
                "change_percent": round(((last - prev) / prev * 100), 2) if prev > 0 else 0.0
            })
        return results
