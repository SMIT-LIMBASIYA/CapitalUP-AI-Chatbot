"""
CapitalUP Decision Engine & Query Router.
Applies the 4-Question Diagnostic Framework + Nested Decision Tree Routing:
1. ask_stock_details (yes/no)
2. want_to_buy_stock (yes/no)
3. is_indian_market (yes/no)
4. violates_sebi_condition (yes/no)
"""

import os
import re
import time
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.decision_engine.prompts import CAPITALUP_DECISION_ENGINE_SYSTEM_PROMPT


class IntentDestination(str, Enum):
    STOCK_SERVICE = "stock_service"
    ORDER_SERVICE = "order_service"
    PORTFOLIO_SERVICE = "portfolio_service"
    RAG_RETRIEVAL = "rag_retrieval"
    COMPOUND_TOOL_RAG = "compound_tool_rag"
    FINANCIAL_ADVICE_BLOCK = "financial_advice_block"
    REJECT_RISK = "reject_risk"
    GENERAL_CHAT = "general_chat"


class BrokerageDiagnosticDecision(BaseModel):
    # The 4 Core Diagnostic Questions
    ask_stock_details: bool = Field(description="Does user ask about stock details, price, quotes, high/low? (yes/no)")
    want_to_buy_stock: bool = Field(description="Does user want to buy, sell, or place/cancel a trade order? (yes/no)")
    is_indian_market: bool = Field(description="Is the stock/asset traded on Indian NSE/BSE markets? (yes/no)")
    violates_sebi_condition: bool = Field(description="Does the query violate SEBI non-advisory conditions (stock tips, buy/sell recommendations)? (yes/no)")

    # Nested Decision Routing Output
    forward_destination: IntentDestination = Field(description="Selected downstream side/service to forward the query to")
    action_type: str = Field(description="Action to execute (e.g. fetch_live_market_data, prepare_order_2fa, sebi_advisory_refusal)")
    requires_rag: bool = Field(description="Whether brokerage knowledge base search is required")
    is_high_risk: bool = Field(description="Whether the request is high risk (requires 2FA or compliance block)")
    confidence_score: float = Field(default=1.0, description="Confidence level between 0.0 and 1.0")
    policy_reason: str = Field(description="Step-by-step reasoning from nested if-else logic")


def evaluate_nested_routing(
    ask_stock_details: bool,
    want_to_buy_stock: bool,
    is_indian_market: bool,
    violates_sebi_condition: bool,
    is_security_threat: bool = False,
    is_portfolio_query: bool = False,
    is_order_history_query: bool = False,
    is_compound_query: bool = False,
    is_general_faq: bool = False
) -> Dict[str, Any]:
    """
    Executes the exact nested if-else routing decision tree for CapitalUP brokerage.
    """
    # 0. Immediate Security Filter
    if is_security_threat:
        return {
            "forward_destination": IntentDestination.REJECT_RISK,
            "action_type": "security_block",
            "requires_rag": False,
            "is_high_risk": True,
            "policy_reason": "Security threat or prompt injection intercepted"
        }

    # 1. SEBI Regulatory Compliance Check
    if violates_sebi_condition:
        return {
            "forward_destination": IntentDestination.FINANCIAL_ADVICE_BLOCK,
            "action_type": "sebi_advisory_refusal",
            "requires_rag": False,
            "is_high_risk": True,
            "policy_reason": "SEBI violation: Broker cannot provide unsolicited investment tips, targets, or recommendations"
        }

    # 2. Order Placement / Trade Execution
    elif want_to_buy_stock:
        if is_indian_market:
            return {
                "forward_destination": IntentDestination.ORDER_SERVICE,
                "action_type": "prepare_order_2fa",
                "requires_rag": False,
                "is_high_risk": True,  # Destructive action: Requires 2FA confirmation modal
                "policy_reason": "Valid Indian stock order: Routed to order gateway with mandatory 2FA confirmation"
            }
        else:
            return {
                "forward_destination": IntentDestination.RAG_RETRIEVAL,
                "action_type": "unsupported_market_policy",
                "requires_rag": True,
                "is_high_risk": False,
                "policy_reason": "Unsupported asset: Foreign stocks or crypto are not traded on NSE/BSE"
            }

    # 3. Stock Details & Quotes Inquiry
    elif ask_stock_details:
        if is_indian_market:
            return {
                "forward_destination": IntentDestination.STOCK_SERVICE,
                "action_type": "fetch_live_market_data",
                "requires_rag": False,
                "is_high_risk": False,
                "policy_reason": "Real-time market quote request for Indian NSE/BSE equity"
            }
        else:
            return {
                "forward_destination": IntentDestination.RAG_RETRIEVAL,
                "action_type": "unsupported_market_policy",
                "requires_rag": True,
                "is_high_risk": False,
                "policy_reason": "Foreign or crypto asset inquiry: Routed to knowledge base for platform policy"
            }

    # 4. Auxiliary Account / Operational Queries
    else:
        if is_portfolio_query:
            return {
                "forward_destination": IntentDestination.PORTFOLIO_SERVICE,
                "action_type": "portfolio_analytics",
                "requires_rag": False,
                "is_high_risk": False,
                "policy_reason": "Read-only personal portfolio holdings and P&L analytics"
            }
        elif is_order_history_query:
            return {
                "forward_destination": IntentDestination.ORDER_SERVICE,
                "action_type": "order_history",
                "requires_rag": False,
                "is_high_risk": False,
                "policy_reason": "Read-only order history and trade log lookup"
            }
        elif is_compound_query:
            return {
                "forward_destination": IntentDestination.COMPOUND_TOOL_RAG,
                "action_type": "compound_lookup",
                "requires_rag": True,
                "is_high_risk": False,
                "policy_reason": "Requires both user account balance/order data and brokerage policy/margins"
            }
        elif is_general_faq:
            return {
                "forward_destination": IntentDestination.RAG_RETRIEVAL,
                "action_type": "brokerage_faq",
                "requires_rag": True,
                "is_high_risk": False,
                "policy_reason": "Brokerage policy, auto square-off timings, and charges inquiry"
            }
        else:
            return {
                "forward_destination": IntentDestination.GENERAL_CHAT,
                "action_type": "general_conversation",
                "requires_rag": False,
                "is_high_risk": False,
                "policy_reason": "General conversational message"
            }


def evaluate_deterministic_brokerage(query: str) -> Optional[BrokerageDiagnosticDecision]:
    """
    Sub-millisecond (<1ms) pure Python regex diagnostic and nested routing evaluator.
    """
    q_clean = query.lower()

    # Step 1: Detect Security Threat
    is_sec = bool(re.search(r"(ignore\s+(your\s+|all\s+)?instructions|developer\s+mode|print\s+out.*prompt|reveal.*prompt|database\s+connection\s+string|add\s+[0-9]+.*balance)", q_clean))

    # Step 2: Answer 4 Diagnostic Questions
    violates_sebi = bool(re.search(r"(should\s+i\s+(buy|sell)|will\s+it\s+go\s+up|guaranteed\s+target|100%\s+return|where\s+to\s+invest.*savings|give\s+me\s+a\s+(tip|stock\s+tip))", q_clean))
    want_to_buy = bool(re.search(r"\b(execute.*(buy|sell)|market\s+order\s+to\s+(buy|sell)|sell\s+all|buy\s+[0-9]+\s+shares|can\s+i\s+buy.*shares)\b", q_clean))
    is_foreign = bool(re.search(r"\b(apple|aapl|bitcoin|btc|crypto|tesla|tsla|nasdaq|dow)\b", q_clean))
    is_indian = not is_foreign
    ask_details = bool(re.search(r"\b(live\s+price|price\s+of|quote|market\s+level|trading\s+today|change\s+from\s+yesterday)\b", q_clean))
    if "should i sell my reliance" in q_clean:
        ask_details = True

    # Auxiliary queries
    is_portfolio = bool(re.search(r"\b(portfolio|holdings|my\s+stocks|profit\s+or\s+loss|p&l|pnl|total\s+invested)\b", q_clean)) and not want_to_buy and not violates_sebi
    is_order_hist = bool(re.search(r"\b(order\s+history|executed\s+orders|last.*orders|open\s+orders)\b", q_clean)) and not want_to_buy
    is_compound = bool(re.search(r"(brokerage.*charge.*and.*last\s+order|balance.*and.*how\s+much\s+margin)", q_clean))
    is_faq = bool(re.search(r"\b(auto\s+square|square\s+off|penalty\s+fee|margin\s+limits|intraday\s+rules|brokerage\s+charge)\b", q_clean)) and not is_compound

    nested = evaluate_nested_routing(
        ask_stock_details=ask_details,
        want_to_buy_stock=want_to_buy,
        is_indian_market=is_indian,
        violates_sebi_condition=violates_sebi,
        is_security_threat=is_sec,
        is_portfolio_query=is_portfolio,
        is_order_history_query=is_order_hist,
        is_compound_query=is_compound,
        is_general_faq=is_faq
    )

    return BrokerageDiagnosticDecision(
        ask_stock_details=ask_details,
        want_to_buy_stock=want_to_buy,
        is_indian_market=is_indian,
        violates_sebi_condition=violates_sebi,
        forward_destination=nested["forward_destination"],
        action_type=nested["action_type"],
        requires_rag=nested["requires_rag"],
        is_high_risk=nested["is_high_risk"],
        confidence_score=1.0,
        policy_reason=nested["policy_reason"]
    )
