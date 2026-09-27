"""
CapitalUP Database Setup & Seeder Script
Initializes PostgreSQL tables (Supabase) and seeds market stocks, indices, and sample user data.
"""

import asyncio
import os
import re
from decimal import Decimal
from dotenv import load_dotenv
import asyncpg

load_dotenv()

STOCKS_DATA = [
    {"symbol": "^NSEI", "company_name": "NIFTY 50", "sector": "Index", "last_price": 25800.00, "market_open": 25750.00, "day_high": 25850.00, "day_low": 25700.00, "previous_close": 25720.00},
    {"symbol": "^BSESN", "company_name": "SENSEX", "sector": "Index", "last_price": 84200.00, "market_open": 84050.00, "day_high": 84350.00, "day_low": 83950.00, "previous_close": 84000.00},
    {"symbol": "RELIANCE.NS", "company_name": "Reliance Industries", "sector": "Energy & Retail", "last_price": 2980.50, "market_open": 2960.00, "day_high": 2995.00, "day_low": 2955.00, "previous_close": 2965.00},
    {"symbol": "TCS.NS", "company_name": "Tata Consultancy Services", "sector": "Information Technology", "last_price": 4250.00, "market_open": 4230.00, "day_high": 4275.00, "day_low": 4210.00, "previous_close": 4220.00},
    {"symbol": "HDFCBANK.NS", "company_name": "HDFC Bank", "sector": "Banking & Finance", "last_price": 1640.25, "market_open": 1630.00, "day_high": 1648.00, "day_low": 1625.00, "previous_close": 1632.00},
    {"symbol": "INFY.NS", "company_name": "Infosys", "sector": "Information Technology", "last_price": 1920.00, "market_open": 1905.00, "day_high": 1935.00, "day_low": 1898.00, "previous_close": 1900.00},
    {"symbol": "ICICIBANK.NS", "company_name": "ICICI Bank", "sector": "Banking & Finance", "last_price": 1210.80, "market_open": 1200.00, "day_high": 1220.00, "day_low": 1195.00, "previous_close": 1202.00},
    {"symbol": "SBIN.NS", "company_name": "State Bank of India", "sector": "Public Banking", "last_price": 785.40, "market_open": 780.00, "day_high": 792.00, "day_low": 778.00, "previous_close": 782.00},
    {"symbol": "BHARTIARTL.NS", "company_name": "Bharti Airtel", "sector": "Telecommunications", "last_price": 1540.00, "market_open": 1525.00, "day_high": 1550.00, "day_low": 1520.00, "previous_close": 1530.00},
    {"symbol": "ITC.NS", "company_name": "ITC", "sector": "FMCG", "last_price": 510.50, "market_open": 508.00, "day_high": 515.00, "day_low": 506.00, "previous_close": 507.00},
    {"symbol": "LT.NS", "company_name": "Larsen & Toubro", "sector": "Infrastructure", "last_price": 3680.00, "market_open": 3650.00, "day_high": 3710.00, "day_low": 3640.00, "previous_close": 3660.00},
    {"symbol": "HINDUNILVR.NS", "company_name": "Hindustan Unilever", "sector": "FMCG", "last_price": 2720.00, "market_open": 2705.00, "day_high": 2740.00, "day_low": 2695.00, "previous_close": 2710.00},
    {"symbol": "BAJFINANCE.NS", "company_name": "Bajaj Finance", "sector": "Financial Services", "last_price": 7450.00, "market_open": 7400.00, "day_high": 7520.00, "day_low": 7380.00, "previous_close": 7410.00},
    {"symbol": "TATAMOTORS.NS", "company_name": "Tata Motors", "sector": "Automotive", "last_price": 965.00, "market_open": 955.00, "day_high": 975.00, "day_low": 950.00, "previous_close": 958.00},
    {"symbol": "KOTAKBANK.NS", "company_name": "Kotak Mahindra Bank", "sector": "Banking & Finance", "last_price": 1820.00, "market_open": 1810.00, "day_high": 1835.00, "day_low": 1805.00, "previous_close": 1815.00},
    {"symbol": "AXISBANK.NS", "company_name": "Axis Bank", "sector": "Banking & Finance", "last_price": 1240.00, "market_open": 1230.00, "day_high": 1250.00, "day_low": 1225.00, "previous_close": 1235.00},
    {"symbol": "MARUTI.NS", "company_name": "Maruti Suzuki", "sector": "Automotive", "last_price": 12400.00, "market_open": 12300.00, "day_high": 12550.00, "day_low": 12250.00, "previous_close": 12320.00},
    {"symbol": "SUNPHARMA.NS", "company_name": "Sun Pharmaceutical", "sector": "Pharmaceuticals", "last_price": 1890.00, "market_open": 1875.00, "day_high": 1905.00, "day_low": 1870.00, "previous_close": 1880.00},
    {"symbol": "TITAN.NS", "company_name": "Titan Company", "sector": "Consumer Goods", "last_price": 3720.00, "market_open": 3700.00, "day_high": 3750.00, "day_low": 3685.00, "previous_close": 3705.00},
    {"symbol": "ADANIENT.NS", "company_name": "Adani Enterprises", "sector": "Conglomerate", "last_price": 3120.00, "market_open": 3080.00, "day_high": 3150.00, "day_low": 3060.00, "previous_close": 3090.00},
    {"symbol": "WIPRO.NS", "company_name": "Wipro", "sector": "Information Technology", "last_price": 540.00, "market_open": 535.00, "day_high": 546.00, "day_low": 532.00, "previous_close": 538.00},
    {"symbol": "ONGC.NS", "company_name": "Oil & Natural Gas Corp", "sector": "Energy", "last_price": 295.00, "market_open": 292.00, "day_high": 298.00, "day_low": 290.00, "previous_close": 293.00},
    {"symbol": "ZOMATO.NS", "company_name": "Zomato Limited", "sector": "Consumer Tech", "last_price": 275.50, "market_open": 270.00, "day_high": 280.00, "day_low": 268.00, "previous_close": 271.00},
    {"symbol": "JIOFIN.NS", "company_name": "Jio Financial Services", "sector": "Financial Services", "last_price": 352.00, "market_open": 348.00, "day_high": 356.00, "day_low": 345.00, "previous_close": 349.00},
    {"symbol": "PAYTM.NS", "company_name": "Paytm (One97 Communications)", "sector": "FinTech", "last_price": 680.00, "market_open": 670.00, "day_high": 692.00, "day_low": 665.00, "previous_close": 675.00},
]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    mobile_number VARCHAR(15) UNIQUE,
    password_hash TEXT NOT NULL DEFAULT 'hashed_pwd',
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    balance NUMERIC(12,2) NOT NULL DEFAULT 15000.00,
    is_email_verified BOOLEAN NOT NULL DEFAULT TRUE,
    is_mobile_verified BOOLEAN NOT NULL DEFAULT TRUE,
    is_name_locked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profile (
    profile_id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    full_name VARCHAR(100),
    father_name VARCHAR(100),
    mother_name VARCHAR(100),
    dob DATE,
    gender VARCHAR(20),
    occupation VARCHAR(100),
    income VARCHAR(50),
    marital_status VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(50) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    exchange VARCHAR(20) NOT NULL DEFAULT 'NSE',
    instrument_type VARCHAR(20) NOT NULL DEFAULT 'EQUITY',
    sector VARCHAR(100),
    last_price NUMERIC(12,2),
    day_high NUMERIC(12,2),
    day_low NUMERIC(12,2),
    market_open NUMERIC(12,2),
    previous_close NUMERIC(12,2),
    price_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    average_buy_price NUMERIC(12,2) NOT NULL CHECK (average_buy_price > 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_portfolio_user_symbol UNIQUE(user_id, symbol)
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price NUMERIC(12,2) NOT NULL CHECK (price > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlists (
    watchlist_id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    symbol VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_symbol UNIQUE(user_id, symbol)
);
"""

def clean_database_url(url: str) -> str:
    if not url:
        raise ValueError("DATABASE_URL is not set in environment!")
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", url)

async def init_db():
    raw_url = os.getenv("DATABASE_URL")
    db_url = clean_database_url(raw_url)
    print("🔌 Connecting to PostgreSQL...")

    conn = await asyncpg.connect(db_url)
    try:
        print("🔨 Executing schema migrations...")
        await conn.execute(SCHEMA_SQL)
        print(" Schema created successfully.")

        print(f"🌱 Seeding {len(STOCKS_DATA)} stocks and indices...")
        for s in STOCKS_DATA:
            await conn.execute(
                """
                INSERT INTO stocks (
                    symbol, company_name, sector, last_price, day_high, day_low, market_open, previous_close
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (symbol) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    sector = EXCLUDED.sector,
                    last_price = EXCLUDED.last_price,
                    day_high = EXCLUDED.day_high,
                    day_low = EXCLUDED.day_low,
                    market_open = EXCLUDED.market_open,
                    previous_close = EXCLUDED.previous_close,
                    price_updated_at = CURRENT_TIMESTAMP;
                """,
                s["symbol"], s["company_name"], s["sector"],
                Decimal(str(s["last_price"])), Decimal(str(s["day_high"])),
                Decimal(str(s["day_low"])), Decimal(str(s["market_open"])),
                Decimal(str(s["previous_close"]))
            )
        print(" Stocks seeded successfully.")

        user_row = await conn.fetchrow("SELECT user_id FROM users WHERE email = 'investor@capitalup.com';")
        if not user_row:
            print("👤 Creating demo investor account...")
            user_id = await conn.fetchval(
                """
                INSERT INTO users (full_name, email, mobile_number, balance)
                VALUES ('Aarav Sharma', 'investor@capitalup.com', '+919876543210', 125000.00)
                RETURNING user_id;
                """
            )
            demo_holdings = [
                (user_id, "RELIANCE.NS", 15, Decimal("2850.00")),
                (user_id, "TCS.NS", 10, Decimal("4100.00")),
                (user_id, "HDFCBANK.NS", 30, Decimal("1580.00")),
                (user_id, "INFY.NS", 25, Decimal("1850.00")),
                (user_id, "ZOMATO.NS", 100, Decimal("210.00")),
            ]
            for h in demo_holdings:
                await conn.execute(
                    """
                    INSERT INTO portfolio_holdings (user_id, symbol, quantity, average_buy_price)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, symbol) DO NOTHING;
                    """,
                    h[0], h[1], h[2], h[3]
                )
            print(" Demo investor and holdings created.")
        else:
            print(" Demo investor already exists.")

    finally:
        await conn.close()
        print(" Connection closed. All set for retrieval!")

if __name__ == "__main__":
    asyncio.run(init_db())
