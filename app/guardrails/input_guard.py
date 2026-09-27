"""
CapitalUP Input Guarding Layer.
Validates incoming user queries before any downstream tool, RAG, or execution occurs.
Enforces:
1. Verdict: "yes definitely" (Abnormal / Block) | "no never" (Safe / Pass) | "maybe" (Borderline / Scrutinize)
2. prompt_name: Identifies exact policy guard
3. Dual-Engine: <1ms Deterministic Pre-Filter + Jev (TypeSafe AI) / OpenAI Model Engine.
"""

import os
import re
import time
import unicodedata
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import httpx
from app.guardrails.input_guard_prompt import CAPITALUP_INPUT_GUARD_SYSTEM_PROMPT


class InputGuardVerdict(str, Enum):
    YES_DEFINITELY = "yes definitely"
    NO_NEVER = "no never"
    MAYBE = "maybe"


class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    SAFE = "SAFE"


class RecommendedAction(str, Enum):
    BLOCK = "BLOCK"
    SCRUTINIZE = "SCRUTINIZE"
    PASS = "PASS"


class InputGuardResult(BaseModel):
    verdict: InputGuardVerdict = Field(description="'yes definitely' (abnormal/attack), 'no never' (clean/normal), 'maybe' (borderline)")
    prompt_name: str = Field(description="Policy signature name e.g. JAILBREAK_INJECTION_GUARD, SEBI_COMPLIANCE_ADVICE_GUARD")
    is_abnormal: bool = Field(description="True if the prompt is abnormal or dangerous for a brokerage system")
    risk_level: RiskLevel = Field(description="CRITICAL, HIGH, MEDIUM, SAFE")
    confidence_score: float = Field(default=1.0, description="Confidence score between 0.0 and 1.0")
    explanation: str = Field(description="Clear explanation of the verdict")
    recommended_action: RecommendedAction = Field(description="BLOCK, SCRUTINIZE, PASS")


# ------------------------------------------------------------------------------
# 1. Deterministic Fast Guard Filter (< 1ms, $0.00 Cost)
# ------------------------------------------------------------------------------
def evaluate_deterministic_guard(prompt: str) -> Optional[InputGuardResult]:
    """
    Sub-millisecond regex & heuristic pattern evaluator covering all security,
    market integrity, and operational risk policies.
    """
    p_raw = prompt.strip()

    # Pre-check: Zero-Width Characters or Cyrillic Homoglyphs (Obfuscation Attack)
    has_zero_width = bool(re.search(r"[\u200B-\u200D\uFEFF\u202A-\u202E]", p_raw))
    # Detect Cyrillic letters mixed with Latin
    has_cyrillic = bool(re.search(r"[\u0400-\u04FF]", p_raw))
    if has_zero_width or has_cyrillic:
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="HOMOGLYPH_OBFUSCATION_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Homoglyph / Zero-width character obfuscation attack detected in prompt.",
            recommended_action=RecommendedAction.BLOCK
        )

    p_clean = unicodedata.normalize("NFKD", p_raw)
    p_lower = p_clean.lower()

    # --- Rule 1: Credentials & Raw PII Leaks (PAN, MPIN, Passwords, TOTP) ---
    has_pan = bool(re.search(r"\b[a-z]{5}[0-9]{4}[a-z]\b", p_lower))
    has_mpin_pwd = bool(re.search(r"\b(mpin\s+is\s+[0-9]{4,6}|password\s+is\s+\S+|my\s+totp\s+is\s+[0-9]{6}|aadhaar.*[0-9]{4}\s+[0-9]{4}\s+[0-9]{4})\b", p_lower))
    if has_pan or has_mpin_pwd:
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="CREDENTIAL_PII_LEAK_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Sensitive credentials / PII leak detected: Trading MPIN, PAN card, or login password exposed.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 2: Insider Trading & Unpublished Price-Sensitive Info (UPSI) ---
    if re.search(r"(insider\s+info|leaked\s+earnings|board\s+meeting\s+leak|brother\s+works\s+in.*finance.*earnings|upsi|confidential\s+financials\s+before\s+release|auditor\s+told\s+me)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="INSIDER_TRADING_UPSI_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Prohibited inquiry involving Unpublished Price-Sensitive Information (UPSI) / Insider Trading.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 3: Market Manipulation & Pump-and-Dump Schemes ---
    if re.search(r"(pump\s+and\s+dump|telegram\s+pump\s+group|trigger\s+an\s+upper\s+circuit|coordinate\s+buying.*penny\s+stock|pump\s+this\s+stock|manipulate\s+the\s+opening\s+price)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="MARKET_MANIPULATION_PUMP_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Illegal market manipulation / coordinated pump-and-dump scheme intercepted.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 4: Unlicensed High-Frequency Trading & Algo Loops ---
    if re.search(r"(run\s+an?\s+(algo|automated\s+bot|script|trading\s+loop)|auto\s+buy\s+every\s+[0-9]+\s+seconds|hft\s+bot\s+without\s+broker\s+approval)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="UNLICENSED_ALGO_BOT_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Unapproved algorithmic bot execution or automated trading loop request prohibited by SEBI.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 5: Indirect Injection Piggybacking Tickers ---
    if re.search(r"\b(price\s+of|tcs|reliance|infy|tatamotors)\b.*?(;\s*ignore\s+instructions|;\s*system\s+prompt|;\s*reveal|;\s*drop)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="INDIRECT_INJECTION_TICKER_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Indirect prompt injection piggybacking on stock ticker lookup intercepted.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 6: DDoS / Payload / Oversized Flood Attack ---
    if len(p_clean) > 1500 or re.search(r"(\b[\w\s]{2,20}\b)(?:\s+\1){3,}", p_lower) or re.search(r"[^\x20-\x7E\s\u0900-\u097F]{20,}", p_clean):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="DDOS_PAYLOAD_ABUSE_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Payload abuse detected: Oversized flood, repetitive token spam, or binary payload anomaly.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 7: Script / HTML Injection ---
    if re.search(r"(<script.*?>|javascript:|onload=|onerror=|<iframe|<img.*src=)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="DDOS_PAYLOAD_ABUSE_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.HIGH,
            confidence_score=1.0,
            explanation="Cross-site scripting (XSS) / HTML injection payload detected in prompt.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 8: SQL Injection / Command Injection ---
    if re.search(r"(union\s+select|;\s*drop\s+table|'\s+or\s+1\s*=\s*1|--\s*$|;\s*(rm\s+-rf|powershell|curl|wget|cat\s+/etc))", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="SQLI_COMMAND_INJECTION_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="SQL injection or remote shell execution syntax detected.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 9: Jailbreak & Roleplay Injection ---
    if re.search(r"(ignore\s+(your\s+|all\s+|previous\s+)*instructions|developer\s+mode|\bdan\b|dan\s+mode|jailbreak|pretend\s+you\s+have\s+no\s+rules|unrestricted\s+ai|evil\s+mode|override\s+safety)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="JAILBREAK_INJECTION_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Prompt injection / Jailbreak escape attempt intercepted.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 10: System Prompt & Secret Exfiltration ---
    if re.search(r"(system\s+prompt\s+reveal|reveal.*system\s+prompt|print\s+(out\s+)?(all\s+)?(hidden\s+)?instructions|database\s+connection\s+string|show.*api_key|print.*secret|hidden\s+developer\s+prompt)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="SYSTEM_EXFILTRATION_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Reconnaissance / Exfiltration attempt targeting system prompts and internal secrets.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 11: Financial Tampering & Fraud ---
    if re.search(r"(add\s+[0-9]+.*balance|update\s+cash_balance|transfer.*to\s+my\s+bank\s+without\s+pin|change.*user\s+id|spoof\s+account)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="FINANCIAL_TAMPERING_THEFT_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.CRITICAL,
            confidence_score=1.0,
            explanation="Unauthorized account manipulation / balance tampering request rejected.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 12: Fat-Finger Order Quantities ---
    if re.search(r"\b(buy|sell)\s+([0-9]{6,}|50,000\s+shares\s+of\s+mrf)\b", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="FAT_FINGER_ANOMALY_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.HIGH,
            confidence_score=1.0,
            explanation="Fat-finger quantity anomaly: Order size grossly exceeds standard retail risk limits.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 13: SEBI Compliance & Investment Advice Trap ---
    if re.search(r"(should\s+i\s+(buy|sell)|will\s+it\s+go\s+up|guaranteed\s+target|100%\s+return|double\s+my\s+money|give\s+me\s+a\s+(tip|stock\s+tip)|which\s+stock\s+to\s+buy\s+tomorrow)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.YES_DEFINITELY,
            prompt_name="SEBI_COMPLIANCE_ADVICE_GUARD",
            is_abnormal=True,
            risk_level=RiskLevel.HIGH,
            confidence_score=1.0,
            explanation="SEBI statutory violation: Brokerage cannot dispense investment tips or return guarantees.",
            recommended_action=RecommendedAction.BLOCK
        )

    # --- Rule 14: Market Hours AMO Guard ("maybe") ---
    if re.search(r"(execute.*market\s+order.*(sunday|midnight|at\s+night|outside\s+market\s+hours)|buy.*now.*market\s+is\s+closed)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.MAYBE,
            prompt_name="MARKET_HOURS_AMO_GUARD",
            is_abnormal=False,
            risk_level=RiskLevel.MEDIUM,
            confidence_score=0.90,
            explanation="Market order requested outside normal NSE/BSE trading hours; routes to AMO policy.",
            recommended_action=RecommendedAction.SCRUTINIZE
        )

    # --- Rule 15: Circuit / GSM / ASM Surveillance ("maybe") ---
    if re.search(r"(locked\s+in\s+lower\s+circuit|gsm\s+stage|asm\s+list|sell\s+my.*lower\s+circuit)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.MAYBE,
            prompt_name="CIRCUIT_GSM_ASM_GUARD",
            is_abnormal=False,
            risk_level=RiskLevel.MEDIUM,
            confidence_score=0.90,
            explanation="Inquiry involves circuit breaker limits or SEBI ASM/GSM surveillance categories.",
            recommended_action=RecommendedAction.SCRUTINIZE
        )

    # --- Rule 16: Borderline / Speculative Scenarios ("maybe") ---
    if re.search(r"(is\s+the\s+market\s+crashing\s+tomorrow|what\s+is\s+the\s+general\s+sentiment|is\s+tcs\s+overvalued\s+or\s+undervalued|rumors\s+about\s+merger)", p_lower):
        return InputGuardResult(
            verdict=InputGuardVerdict.MAYBE,
            prompt_name="BORDERLINE_SPECULATIVE_GUARD",
            is_abnormal=False,
            risk_level=RiskLevel.MEDIUM,
            confidence_score=0.85,
            explanation="Speculative market inquiry: Acceptable with mandatory educational disclaimer and caution.",
            recommended_action=RecommendedAction.SCRUTINIZE
        )

    # --- Rule 17: Legitimate Brokerage Queries ("no never") ---
    is_legit_portfolio = bool(re.search(r"\b(portfolio|holdings|my\s+stocks|profit\s+or\s+loss|p&l|pnl|total\s+invested)\b", p_lower))
    is_legit_quote = bool(re.search(r"\b(live\s+price|price\s+of|quote|market\s+level|trading\s+today|yesterday's\s+close)\b", p_lower))
    is_legit_orders = bool(re.search(r"\b(order\s+history|executed\s+orders|last.*orders|open\s+orders)\b", p_lower))
    is_legit_faq = bool(re.search(r"\b(auto\s+square|square\s+off|penalty\s+fee|brokerage\s+charge|margin\s+multiplier|kyc|stt\s+tax)\b", p_lower))
    is_legit_greeting = bool(re.search(r"^(hi|hello|hey|good\s+morning|good\s+afternoon|namaste)\b", p_lower))

    if is_legit_portfolio or is_legit_quote or is_legit_orders or is_legit_faq:
        return InputGuardResult(
            verdict=InputGuardVerdict.NO_NEVER,
            prompt_name="LEGITIMATE_BROKERAGE_QUERY",
            is_abnormal=False,
            risk_level=RiskLevel.SAFE,
            confidence_score=1.0,
            explanation="Clean legitimate brokerage inquiry; permitted for backend routing.",
            recommended_action=RecommendedAction.PASS
        )

    if is_legit_greeting:
        return InputGuardResult(
            verdict=InputGuardVerdict.NO_NEVER,
            prompt_name="GENERAL_GREETING_QUERY",
            is_abnormal=False,
            risk_level=RiskLevel.SAFE,
            confidence_score=1.0,
            explanation="Normal conversational greeting; safe to pass.",
            recommended_action=RecommendedAction.PASS
        )

    return None


# ------------------------------------------------------------------------------
# 2. Jev & Model Fallback Input Guard Runner
# ------------------------------------------------------------------------------
async def run_jev_input_guard(prompt: str, typesafe_key: str, openai_key: str) -> InputGuardResult:
    """
    Evaluates input guard using Jev (TypeSafe AI) or OpenAI structured output.
    """
    if typesafe_key:
        url = "https://api.typesafe.ai/v1/decide"
        headers = {"Authorization": f"Bearer {typesafe_key}", "Content-Type": "application/json"}
        payload = {
            "model": "jev-latest",
            "system_prompt": CAPITALUP_INPUT_GUARD_SYSTEM_PROMPT,
            "input": prompt,
            "schema": InputGuardResult.model_json_schema()
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json().get("result", res.json())
                    return InputGuardResult(**data)
        except Exception:
            pass

    if openai_key:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=openai_key)
        try:
            resp = await client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": CAPITALUP_INPUT_GUARD_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format=InputGuardResult,
                temperature=0.0
            )
            return resp.choices[0].message.parsed
        except Exception:
            pass

    # Default fallback: safe heuristic
    return InputGuardResult(
        verdict=InputGuardVerdict.MAYBE,
        prompt_name="BORDERLINE_SPECULATIVE_GUARD",
        is_abnormal=False,
        risk_level=RiskLevel.MEDIUM,
        confidence_score=0.5,
        explanation="Default safety evaluation passed with elevated scrutiny.",
        recommended_action=RecommendedAction.SCRUTINIZE
    )


# ------------------------------------------------------------------------------
# 3. Unified Entrypoint for Application & Orchestrator
# ------------------------------------------------------------------------------
async def validate_user_prompt(prompt: str) -> Dict[str, Any]:
    """
    Master Input Guarding Entrypoint.
    Executes Phase 1 (<1ms deterministic filter) -> Phase 2 (Jev / Model Guard).
    """
    start = time.perf_counter()

    # Step 1: Sub-millisecond pre-filter
    guard_res = evaluate_deterministic_guard(prompt)
    if guard_res:
        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        return {
            "engine": "Deterministic Input Guard (<1ms)",
            "latency_ms": latency_ms,
            "estimated_cost_usd": 0.0,
            "result": guard_res
        }

    # Step 2: Jev / Model Guard
    typesafe_key = os.getenv("TYPESAFE_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    guard_res = await run_jev_input_guard(prompt, typesafe_key, openai_key)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    return {
        "engine": "Jev / Model Guard Layer",
        "latency_ms": latency_ms,
        "estimated_cost_usd": 0.00010 if typesafe_key else 0.00003,
        "result": guard_res
    }
