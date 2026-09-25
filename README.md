# CapitalUP: Real-Time Brokerage AI Chatbot Architecture

A high-throughput, low-latency, and cost-efficient conversational AI engine engineered specifically for **CapitalUP** (Real-Time Brokerage System). 

This system handles portfolio inquiries, real-time market insights, trade/order history analytics, and regulatory RAG, backed by a **deterministic-first Decision Engine**, **Redis multi-tiered caching**, **hybrid RAG**, and **output safety guardrails**.

---

## 🏛️ System Architecture Overview

The system strictly follows the **Scalable RAG + Decision Engine Architecture**:

```
                       [1. Client Layer]
           (Web App / Mobile App / API Clients)
                           │
                           ▼
                 [2. Edge Controls]
         (Cloudflare CDN/WAF ──► Kong API Gateway)
       (Auth / JWT, Rate Limiting, Tenant Isolation)
                           │
                           ▼
          [3. AI Orchestrator Service (Stateless)]
         FastAPI + Async Event Loop + SSE Streaming
          ├── Cache Lookup ◄──► [4. Redis Cluster]
          │                         ├── Exact Cache (O(1))
          │                         └── Semantic Cache (RedisVL)
          │
          ├── Evaluates ────► [Decision Engine]
          │                     ├── 1. Deterministic Policies / Rules (Regex & JSON-Logic: <2ms)
          │                     └── 2. Fast Intent & Risk Classifier (OpenAI gpt-4o-mini / Structured Outputs)
          │
          ├── Triggers ─────► [5. Service / Tool Layer]
          │                     ├── Portfolio, Transaction, Order, Ledger Services
          │                     └── PostgreSQL + Redis Hot State + DuckDB/Polars
          │
          ├── Queries ──────► [6. RAG Pipeline]
          │                     ├── Hybrid Search (Dense Vector + BM25)
          │                     └── Qdrant Cluster + Reranker
          │
          └── Dispatches ───► [7. LLM Layer]
                                ├── Model Gateway (LiteLLM)
                                ├── Small/Cheap LLM (Fast, high-volume)
                                └── Big LLM (Complex financial reasoning)
                                        │
                                        ▼
                           [8. Output Safety & Validation]
                            (Presidio PII + NeMo Guardrails)
                                        │
                                        ▼
                                 [User Response]
                           (Real-time SSE Token Stream)
```

---

## 🧩 Architectural Layers & Technology Stack

### 1. Client Layer & Edge Controls
* **Entrypoint:** Web (React/Next.js), Mobile (iOS/Android), and Internal API Clients.
* **WAF / CDN:** Cloudflare for DDoS protection and TLS termination.
* **API Gateway:** Kong / Traefik with JWT validation, rate-limiting, and tenant isolation headers (`X-Tenant-ID`, `X-Request-ID`).

### 2. Stateless AI Orchestrator Service
* **Technology:** **FastAPI** + **Uvicorn** + **AsyncIO**.
* **Role:** Parses incoming user queries, manages conversation session IDs, coordinates the Decision Engine, schedules async tool execution, and streams real-time tokens to clients via **Server-Sent Events (SSE)**.

### 3. Redis Cluster (Caching & Session State)
* **Exact Response Cache:** Fast key-value hashing ($O(1)$) with TTL for repeated static queries (e.g., brokerage charges, FAQs).
* **Semantic Cache:** Powered by **RedisVL** (Redis Vector Library). Compares vector similarity of incoming queries against cached answers. If similarity $>0.92$, returns response in $<5\text{ms}$ with **$0 LLM cost**.
* **Session State:** Short-lived conversational memory sliding window.
* **Rate Limiting:** Sliding-window token-bucket per user/IP.

### 4. Decision Engine (Deterministic Rules + OpenAI Fast Structured Classifier)
To maximize throughput, minimize cost, and prevent latency spikes, the decision pipeline operates in two phases:

1. **Deterministic Rule Layer (<2ms, $0 cost):**
   * Evaluated via `json-logic` and pre-compiled regex patterns.
   * Handles direct keyword matches (e.g., exact matches for *"balance"*, *"portfolio"*, *"holdings"*).
   * Instantly routes to the corresponding business tool without invoking any model.

2. **OpenAI Fast Decision Model (`gpt-4o-mini` with Structured Outputs):**
   * Powered by **OpenAI `gpt-4o-mini`** utilizing **Instructor / Pydantic** structured schema validation.
   * Runs in fast JSON mode, guaranteeing 100% schema compliance with zero formatting errors.
   * **Key Responsibilities:**
     * **Tool Routing:** Determines the destination `[PORTFOLIO_SERVICE, ORDER_SERVICE, RAG_RETRIEVAL, DIRECT_LLM]`.
     * **Safety & Risk Check:** Evaluates whether the user's prompt is a high-risk trading command requiring 2FA or explicit confirmation.
     * **RAG Retrieval Gating:** Detects if regulatory or brokerage documentation search is strictly necessary.
   * *Note:* The architecture is fully modular, allowing plug-and-play migration to dedicated decision engines (e.g., TypeSafe Jev) in future versions.

### 5. Service / Tool Layer (Brokerage Business Logic & Analytics)
* **Services:** Portfolio Service, Transaction Service, Order Service, Ledger Service, Risk Service.
* **Storage & State:**
  * **PostgreSQL (Primary + Read Replicas):** ACID transactions, user accounts, order ledger.
  * **Redis:** Live ticker prices, real-time order status, margin limits, and pub/sub cache invalidation.
* **Analytics Engine:** **Polars** + **DuckDB** for in-memory computations (P&L calculations, risk exposure, historical trade analytics) at vectorized speed.

### 6. RAG Pipeline (Retrieval Augmented Generation)
* **Vector Database:** **Qdrant Cluster** (Rust-based, sub-10ms search, horizontal scaling, payload ACL filtering).
* **Retrieval Mode:** **Hybrid Retrieval** (Dense embeddings + BM25 keyword matching) to catch financial terminology and exact ticker symbols.
* **Embeddings:** `bge-small-en-v1.5` or `text-embedding-3-small`.
* **Reranker:** Cross-Encoder reranker (`bge-reranker-v2-m3` or Cohere) applied only to top-10 candidates to minimize latency.
* **Asynchronous Ingestion Pipeline:** Celery/Temporal workers parse regulatory documents, brokerage policies, and FAQs, chunking them into Qdrant with tenant and role-based ACLs.

### 7. LLM Layer & Model Gateway
* **Model Gateway:** **LiteLLM** for provider routing, automatic retries, latency timeouts, fallback switching, and strict token budget enforcement.
* **Tiered Model Routing:**
  * **Small / Cheap LLM:** (Gemini 1.5 Flash / Claude 3.5 Haiku) $\rightarrow$ Used for query rewrites, intent classification, and straightforward financial summaries.
  * **Big LLM:** (Claude 3.5 Sonnet / GPT-4o) $\rightarrow$ Reserved exclusively for multi-step reasoning, complex portfolio risk synthesis, and edge-case resolution.

### 8. Output Safety & Validation
* **PII Detection & Redaction:** **Microsoft Presidio** automatically detects and masks credit card numbers, PAN/SSN, bank accounts, and sensitive identity details.
* **Compliance Guardrails:** **NeMo Guardrails** enforces strict policies preventing illegal financial advice disclaimers, prompt injections, and off-topic conversations.
* **Schema Validation:** **Pydantic** ensures tool parameters and API responses strictly adhere to structured JSON contracts.

### 9. Reliability, Observability & Infrastructure
* **Container Orchestration:** Kubernetes (EKS / GKE) with Multi-AZ high availability.
* **Metrics & Tracing:** Prometheus, Grafana, OpenTelemetry, and **Langfuse** for detailed LLM token tracking, cost monitoring, and trace visualization.

---

## 📂 Recommended Directory Structure

```text
d:/VSCODE-PROJECTS/RAG_2_NEW/
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   ├── settings.py             # Pydantic environment configurations
│   └── rules.json              # Deterministic Decision Engine policies
├── app/
│   ├── main.py                 # FastAPI application initialization & SSE routes
│   ├── orchestrator/
│   │   ├── engine.py           # Core stateless orchestration loop
│   │   └── session.py          # Session and context management
│   ├── cache/
│   │   ├── redis_client.py     # Redis exact KV cache & rate limiting
│   │   └── semantic_cache.py   # RedisVL semantic cache manager
│   ├── decision_engine/
│   │   ├── deterministic.py    # Fast rule evaluator (JSON-logic / JEV)
│   │   └── classifier.py       # SLM-assisted fallback classifier
│   ├── tools/
│   │   ├── portfolio.py        # Portfolio & balance tool
│   │   ├── orders.py           # Order service integrations
│   │   ├── analytics.py        # DuckDB / Polars financial calculations
│   │   └── db.py               # Async PostgreSQL database connectors
│   ├── rag/
│   │   ├── vector_store.py     # Qdrant client & collection management
│   │   ├── embeddings.py       # Embedding generation service
│   │   ├── hybrid_search.py    # Dense + BM25 retriever
│   │   └── ingestion.py        # Async PDF/Doc ingestion worker
│   ├── llm/
│   │   ├── gateway.py          # LiteLLM gateway with fallback logic
│   │   └── prompts.py          # System prompts and financial guardrail templates
│   └── safety/
│       ├── pii_masking.py      # Presidio analyzer and anonymizer
│       └── guardrails.py       # NeMo / policy compliance checker
└── tests/
    ├── test_decision_engine.py
    ├── test_cache.py
    └── test_rag.py
```

---

## ⚡ Quickstart & Installation

### 1. Prerequisites
* Python 3.10+
* Docker & Docker Compose (for local Redis, Qdrant, and PostgreSQL)

### 2. Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Application
APP_ENV=development
PORT=8000

# Redis (Caching & Session)
REDIS_URL=redis://localhost:6379/0

# Vector Database (Qdrant)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key

# PostgreSQL (Brokerage Services)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/capitalup_db

# Decision Engine (OpenAI Model)
DECISION_MODEL=gpt-4o-mini

# LLM Providers (via LiteLLM)
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key

# Observability (Langfuse)
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 4. Run the Orchestrator
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🎯 Latency & Cost Optimization Checklist

| Technique | Latency Impact | Cost Impact |
| :--- | :--- | :--- |
| **Exact Hash Cache ($O(1)$)** | Saves $1000\text{ms} \rightarrow <1\text{ms}$ | **100% savings** on hit |
| **Semantic Cache (RedisVL)** | Saves $800\text{ms} \rightarrow <10\text{ms}$ | **100% savings** on hit |
| **Deterministic Rule Engine** | Bypasses LLM routing in $<2\text{ms}$ | **100% routing cost saved** |
| **Dual-Tier LLM (Flash / Haiku)** | First token in $<350\text{ms}$ | **85-90% cheaper** than Frontier models |
| **Hybrid Async Scatter-Gather** | RAG + Tool fetch run in parallel | **50% lower multi-data latency** |
