"""
Service / Tool Layer Exports for CapitalUP.
Provides unified dispatching for AI Orchestrator and Decision Engine.
"""

from app.tools.stock_service import get_stock_quote, get_all_stocks, get_market_indices
from app.tools.portfolio_service import get_user_portfolio
from app.tools.order_service import get_user_orders, get_pending_orders
from app.tools.account_service import get_user_balance, get_user_profile

TOOL_REGISTRY = {
    "get_stock_quote": get_stock_quote,
    "get_market_indices": get_market_indices,
    "get_all_stocks": get_all_stocks,
    "get_user_portfolio": get_user_portfolio,
    "get_user_orders": get_user_orders,
    "get_pending_orders": get_pending_orders,
    "get_user_balance": get_user_balance,
    "get_user_profile": get_user_profile,
}

__all__ = [
    "get_stock_quote",
    "get_market_indices",
    "get_all_stocks",
    "get_user_portfolio",
    "get_user_orders",
    "get_pending_orders",
    "get_user_balance",
    "get_user_profile",
    "TOOL_REGISTRY"
]
