"""
User Account, Balance, and Profile Retrieval Service.
"""

from typing import Dict, Any, Optional
from app.db.connection import get_db_pool

async def get_user_balance(user_id: int = 1) -> Optional[Dict[str, Any]]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, full_name, email, balance, is_email_verified, is_mobile_verified
            FROM users
            WHERE user_id = $1;
            """,
            user_id
        )
        if not row:
            return None

        balance = float(row["balance"])
        return {
            "user_id": row["user_id"],
            "full_name": row["full_name"],
            "available_cash": balance,
            "margin_multiplier": 4.0,
            "intraday_margin_available": round(balance * 4.0, 2),
            "currency": "INR",
            "is_verified": row["is_email_verified"] and row["is_mobile_verified"]
        }

async def get_user_profile(user_id: int = 1) -> Optional[Dict[str, Any]]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.user_id, u.full_name, u.email, u.mobile_number, u.balance,
                   p.city, p.state, p.occupation, p.income
            FROM users u
            LEFT JOIN user_profile p ON u.user_id = p.user_id
            WHERE u.user_id = $1;
            """,
            user_id
        )
        if not row:
            return None

        return {
            "user_id": row["user_id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "mobile": row["mobile_number"],
            "balance": float(row["balance"]),
            "city": row["city"],
            "state": row["state"],
            "occupation": row["occupation"],
            "income_bracket": row["income"]
        }
