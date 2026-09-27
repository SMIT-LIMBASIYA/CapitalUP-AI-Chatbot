"""
CapitalUP Database Retrieval Verification Script
Runs quick diagnostics on PostgreSQL connection, stock lookup, portfolio, and balance.
"""

import asyncio
from app.db.connection import get_db_pool, close_db_pool
from app.tools.stock_service import get_stock_quote, get_market_indices
from app.tools.portfolio_service import get_user_portfolio
from app.tools.account_service import get_user_balance

async def test_retrieval():
    print("=" * 60)
    print("🔍 Testing CapitalUP PostgreSQL Retrieval Layer")
    print("=" * 60)

    try:
        pool = await get_db_pool()
        print(" Connected to Supabase PostgreSQL.")

        # 1. Test Market Indices
        print("\n📈 1. Testing Market Indices Retrieval:")
        indices = await get_market_indices()
        for idx in indices:
            print(f"   • {idx['name']} ({idx['symbol']}): {idx['current_level']} ({idx['change_percent']}%)")

        # 2. Test Stock Quote by Symbol & Fuzzy Name
        print("\n🏢 2. Testing Stock Quote Lookup:")
        tcs = await get_stock_quote("TCS.NS")
        print(f"   • Symbol 'TCS.NS': {tcs}")

        reliance = await get_stock_quote("Reliance")
        print(f"   • Fuzzy 'Reliance': {reliance}")

        # 3. Test User Balance
        print("\n💰 3. Testing User Balance:")
        balance = await get_user_balance(1)
        print(f"   • User 1 Balance: {balance}")

        # 4. Test Portfolio Holdings
        print("\n📊 4. Testing User Portfolio:")
        portfolio = await get_user_portfolio(1)
        print(f"   • Total Invested: ₹{portfolio['total_invested']}")
        print(f"   • Current Value: ₹{portfolio['total_current_value']}")
        print(f"   • Total P&L: ₹{portfolio['total_unrealized_pnl']} ({portfolio['total_unrealized_pnl_percent']}%)")
        print(f"   • Holdings count: {portfolio['holdings_count']}")
        for h in portfolio['holdings']:
            print(f"     - {h['symbol']}: {h['quantity']} shares @ ₹{h['average_buy_price']} (Current: ₹{h['current_price']}, P&L: ₹{h['unrealized_pnl']})")

        print("\n All database retrieval tests passed successfully!")

    except Exception as e:
        print(f"\n❌ Error during retrieval: {e}")
        print("💡 Hint: If tables are not initialized yet, run: python DB_SETUP/setup_db.py")

    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(test_retrieval())
