# CapitalUP: Real-Time Brokerage AI Chatbot

A high-performance, low-latency, and cost-efficient conversational AI engine engineered for **CapitalUP** (Real-Time Brokerage System). 

---

## 🏛️ System Architecture

The chatbot follows a **Scalable RAG + Decision Engine Architecture**:

```
                       [1. Client Layer]
            (Web App / Mobile App / API Clients)
                           │
                           ▼
                 [2. Edge Controls]
         (Cloudflare CDN/WAF ──► API Gateway)
       (Auth / JWT, Rate Limiting, Tenant Isolation)
                           │
                           ▼
          [3. AI Orchestrator Service (Stateless)]
         FastAPI + Async Event Loop + SSE Streaming
          ├── Cache Lookup ◄──► [4. Redis Cloud]
          │                         ├── Exact Cache (O(1))
          │                         └── Semantic Cache (RedisVL)
          │
          ├── Evaluates ────► [Decision Engine]
          │                     ├── 1. Deterministic Policies / Rules (Regex: <2ms)
          │                     └── 2. Fast Intent Router (OpenAI gpt-4o-mini)
          │
          ├── Triggers ─────► [5. Service / Tool Layer]
          │                     ├── Stocks, Portfolio, Orders, Account Services
          │                     └── Supabase PostgreSQL (Live Quotes & Holdings)
          │
          ├── Queries ──────► [6. RAG Pipeline]
          │                     ├── Hybrid Search (Dense Vector + BM25)
          │                     └── Qdrant Cloud + Reranker
          │
          └── Dispatches ───► [7. LLM Layer]
                                ├── Small/Cheap LLM (gpt-4o-mini)
                                └── Big LLM (gpt-4o for complex reasoning)
                                        │
                                        ▼
                           [8. Output Safety & Validation]
                            (Presidio PII + Guardrails)
                                        │
                                        ▼
                                 [User Response]
                           (Real-time SSE Token Stream)
```

---

## ⚙️ Quickstart & Setup Guide

### 1. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your cloud service credentials:

### 4. Initialize Database & Seed Market Assets
Creates all schema tables in PostgreSQL and seeds 25 market stocks and indices:
```bash
python DB_SETUP/setup_db.py
```

### 5. Verify Live Retrieval
Tests live database connections, stock quotes, balance, and portfolio P&L calculations:
```bash
python test_db_retrieval.py
```

---

## 📈 Supported Market Assets (25 Equities & Indices)

* **Market Indices:** `^NSEI` (NIFTY 50), `^BSESN` (SENSEX)
* **IT & Technology:** `TCS.NS`, `INFY.NS`, `WIPRO.NS`, `ZOMATO.NS`, `PAYTM.NS`
* **Banking & Finance:** `HDFCBANK.NS`, `ICICIBANK.NS`, `SBIN.NS`, `KOTAKBANK.NS`, `AXISBANK.NS`, `BAJFINANCE.NS`, `JIOFIN.NS`
* **Energy & Conglomerate:** `RELIANCE.NS`, `ADANIENT.NS`, `ONGC.NS`
* **Auto & Manufacturing:** `TATAMOTORS.NS`, `MARUTI.NS`, `LT.NS` (Larsen & Toubro)
* **FMCG & Consumer:** `ITC.NS`, `HINDUNILVR.NS`, `TITAN.NS`
* **Pharma & Telecom:** `SUNPHARMA.NS`, `BHARTIARTL.NS`

---

## 🚀 Future Roadmap & Next Steps

Points to implement in upcoming phases:

1. **Fast Decision Engine (`app/decision_engine/`):**
   * **Jev (TypeSafe AI) System One Model (`jev-latest`)**: Ultra-fast (70–300ms) non-generative, typed decisions (Choice routing, Risk probability scoring, RAG gating) with zero hallucination.
   * **OpenAI `gpt-4o-mini` Fallback**: Strict Pydantic schema validation as secondary decision router.
   * **Deterministic Filter (<2ms)**: Immediate regex/keyword interception for static commands ($0 cost).

2. **Redis Cloud Multi-Tier Caching & Embeddings (`app/cache/`):**
   * **Embedding Model (`text-embedding-3-small`)**: 1536-dimensional embeddings for Qdrant Cloud hybrid retrieval and RedisVL vector cache.
   * **Semantic Cache (RedisVL)**: Sub-10ms cache hit for repetitive queries, saving 100% of LLM costs.
   * **Exact Hash Cache**: $O(1)$ key-value lookup for repeated static inquiries.
   * **Session State**: Sliding-window conversation history and rate limiting.

3. **RAG Pipeline (`app/rag/`):**
   * Qdrant Cloud hybrid search (dense embeddings + BM25 keyword search).
   * Asynchronous ingestion of brokerage trading rules, margin policies, and compliance FAQs.
   * Context reranking for high-precision regulatory answers.

4. **AI Orchestrator API (`app/main.py`):**
   * Stateless FastAPI application.
   * Real-time Server-Sent Events (SSE) token streaming to Web and Mobile clients.
   * Parallel scatter-gather execution of tool calls and RAG context.

5. **Output Safety & Guardrails (`app/safety/`):**
   * Microsoft Presidio for automated PII detection & masking (PAN, bank accounts, personal info).
   * NeMo Guardrails to prevent unauthorized financial advice and ensure compliance.

6. **Observability & Analytics (`app/monitoring/`):**
   * Langfuse Cloud integration for trace logging, latency tracking, and LLM token cost control.
   * Prometheus metrics exporter for API throughput and health monitoring.
