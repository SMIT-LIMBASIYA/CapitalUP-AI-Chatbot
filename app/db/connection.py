"""
Database connection pool manager using asyncpg for PostgreSQL (Supabase).
"""

import os
import re
import asyncpg
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

_pool: Optional[asyncpg.Pool] = None

def get_clean_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "")
    if not raw_url:
        raise ValueError("DATABASE_URL is not set in environment!")
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw_url)

async def init_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        db_url = get_clean_database_url()
        _pool = await asyncpg.create_pool(
            dsn=db_url,
            min_size=2,
            max_size=10,
            command_timeout=10,
            ssl="require" if "supabase" in db_url or "neon" in db_url else None
        )
    return _pool

async def get_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await init_db_pool()
    return _pool

async def close_db_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
