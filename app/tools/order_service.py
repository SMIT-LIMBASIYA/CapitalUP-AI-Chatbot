"""
Order and Execution Retrieval Service.
"""

from typing import Dict, Any, List
from app.db.connection import get_db_pool

async def get_user_orders(user_id: int = 1, limit: int = 10) -> List[Dict[str, Any]]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT o.id, o.symbol, o.side, o.quantity, o.price, o.status, o.created_at,
                   s.company_name
            FROM orders o
            LEFT JOIN stocks s ON o.symbol = s.symbol
            WHERE o.user_id = $1
            ORDER BY o.created_at DESC
            LIMIT $2;
            """,
            user_id, limit
        )

        return [
            {
                "order_id": str(r["id"]),
                "symbol": r["symbol"],
                "company_name": r["company_name"] or r["symbol"],
                "side": r["side"],
                "quantity": r["quantity"],
                "price": float(r["price"]),
                "total_amount": round(r["quantity"] * float(r["price"]), 2),
                "status": r["status"],
                "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r["created_at"] else None
            }
            for r in rows
        ]

async def get_pending_orders(user_id: int = 1) -> List[Dict[str, Any]]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, symbol, side, quantity, price, status, created_at
            FROM orders
            WHERE user_id = $1 AND status IN ('PENDING', 'OPEN', 'PARTIALLY_FILLED')
            ORDER BY created_at DESC;
            """,
            user_id
        )
        return [
            {
                "order_id": str(r["id"]),
                "symbol": r["symbol"],
                "side": r["side"],
                "quantity": r["quantity"],
                "price": float(r["price"]),
                "status": r["status"],
                "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r["created_at"] else None
            }
            for r in rows
        ]
