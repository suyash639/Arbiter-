# Arbiter

### Production-Grade Multi-Agent Financial AI Operations Platform

> **Arbiter** is a safety-first multi-agent financial AI platform that routes natural-language operations requests to domain-specialist agents while enforcing deterministic tool verification, strict client scope isolation, defense-in-depth security, classification-aware reliability, and structured microsecond observability.

---

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React_19-TypeScript-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/Vite-8.0-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/Agno-Framework-FF6B6B?style=for-the-badge" alt="Agno" />
  <img src="https://img.shields.io/badge/Gemini-3.6_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Backend_Tests-390_Passed-2ea44f?style=flat-square" alt="Backend Tests: 390 Passed" />
  <img src="https://img.shields.io/badge/Frontend_Tests-10_Passed-2ea44f?style=flat-square" alt="Frontend Tests: 10 Passed" />
  <img src="https://img.shields.io/badge/Offline_Benchmark-45%2F45_Passed_(100%25)-2ea44f?style=flat-square" alt="Benchmark: 100%" />
  <img src="https://img.shields.io/badge/Verified_Tools-24_Deterministic-blue?style=flat-square" alt="24 Verified Tools" />
  <img src="https://img.shields.io/badge/Specialist_Agents-6_Active-blueviolet?style=flat-square" alt="6 Agents" />
  <img src="https://img.shields.io/badge/Financial_Math-100%25_Decimal-orange?style=flat-square" alt="100% Decimal Math" />
</p>

---

## 1. System Architecture Overview

```mermaid
flowchart TD
    classDef clientStyle fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef boundaryStyle fill:#0f172a,stroke:#64748b,stroke-width:1px,color:#cbd5e1;
    classDef securityStyle fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fee2e2;
    classDef coreStyle fill:#14532d,stroke:#22c55e,stroke-width:2px,color:#f0fdf4;
    classDef toolStyle fill:#172554,stroke:#3b82f6,stroke-width:2px,color:#eff6ff;
    classDef obsStyle fill:#3b0764,stroke:#a855f7,stroke-width:1px,color:#faf5ff;

    subgraph CLIENT_TIER [" Client & Presentation Layer "]
        User((" Analyst / User ")) -->|Natural Query| UI[" React 19 Operations Console <br/>(TypeScript + Vite + Tailwind) "]
        UI -->|Typed HTTP / JSON| API[" FastAPI Service Boundary <br/>(/v1/query, /health, /ready, /v1/metadata) "]
    end

    subgraph INGRESS_SECURITY [" Ingress Security & Context "]
        API -->|Transport Validation| SEC_PRE[" Security Preflight <br/>(Length Guard & Prompt Injection Scanner) "]
        SEC_PRE -->|Context Binding| CTX[" Request Context Manager <br/>(req_id, client_id, Monotonic Clock) "]
    end

    subgraph MULTI_AGENT_CORE [" Arbiter Multi-Agent Orchestrator "]
        CTX --> ORCH[" ArbiterOrchestrator "]
        ORCH --> ROUTER{" Router & Intent Classifier "}
        ROUTER -->|Book Queries| B_QA[" Book QA Agent "]
        ROUTER -->|KYC & Risk| KYC[" KYC Profile Agent "]
        ROUTER -->|Memos & Notes| NOTES[" Notes Desk Agent "]
        ROUTER -->|Markets & Stocks| MKT[" Market Desk Agent "]
        ROUTER -->|Advice & Violations| COMP[" Compliance Agent <br/>(Zero Tools / Policy Refusal) "]
    end

    subgraph TOOL_VERIFICATION [" Tool Verification & Deterministic Execution Layer "]
        B_QA & KYC & NOTES & MKT -->|Tool Invocation Request| TV_AUTH[" 1. Agent Authorization Gate "]
        TV_AUTH --> TV_SCOPE[" 2. Client Scope Isolation Validation "]
        TV_SCOPE --> TV_SCHEMA[" 3. Strict Pydantic Argument Schema "]
        TV_SCHEMA --> TV_EXEC[" 4. Deterministic Python Tool Execution <br/>(100% Decimal Math & In-Memory Store) "]
        TV_EXEC --> TV_RES[" 5. Result Shape & Citation Validation "]
    end

    subgraph RELIABILITY_ENGINE [" Reliability & Fault Tolerance Subsystem "]
        TV_RES -.->|Upstream Failures / Timeouts| REL_ENG[" ReliabilityEngine <br/>(Classifier + Exponential Jitter Retries + CircuitBreaker) "]
        REL_ENG -.->|Exhausted / Outage| FALLBACK[" Safe Schema-Valid Abstention Envelope "]
    end

    subgraph EGRESS_SECURITY [" Egress Security & Sanitization "]
        TV_RES --> SEC_POST[" Output Security Guard <br/>(PAN & Bank Masking, Citation Grounding) "]
        COMP --> SEC_POST
        FALLBACK --> SEC_POST
        SEC_POST --> ANSWER[" Structured AnswerSchema JSON "]
        ANSWER --> API
    end

    subgraph OBS_SUBSYSTEM [" Full-Pipeline Monotonic Observability "]
        CTX -.-> OBS[" ObservabilityManager <br/>(Monotonic Profiling, Redacted Traces, Token Cost Attribution) "]
        ORCH -.-> OBS
        TV_EXEC -.-> OBS
        SEC_PRE -.-> OBS
        SEC_POST -.-> OBS
    end

    class UI,API clientStyle;
    class SEC_PRE,SEC_POST,TV_AUTH,TV_SCOPE,TV_SCHEMA securityStyle;
    class ORCH,ROUTER,B_QA,KYC,NOTES,MKT,COMP coreStyle;
    class TV_EXEC,TV_RES toolStyle;
    class OBS,CTX,REL_ENG,FALLBACK obsStyle;
```

---

## 2. Engineering Snapshot

| Metric / Dimension | Verified Value | Implementation Detail |
| :--- | :---: | :--- |
| **Backend Test Suite** | **`390 / 390 PASSED`** | 100% unit and integration pass rate across all subsystems (`pytest`) |
| **Frontend Test Suite** | **`10 / 10 PASSED`** | React 19 component and typed API client test coverage (`vitest`) |
| **Offline Evaluation Benchmark** | **`45 / 45 PASSED (100.0%)`** | Zero-drift offline evaluation suite with strict numerical tolerances |
| **Registered Deterministic Tools** | **`24 Tools`** | Declarative registry enforcing agent permissions and argument schemas |
| **Specialist Agents** | **`6 Agents`** | Hub router, 4 deterministic domain specialists, 1 refusal-only compliance agent |
| **Financial Arithmetic Engine** | **`100% Decimal`** | Zero floating-point drift; penny-accurate ledger aggregations via `decimal.Decimal` |
| **Test Suite Execution Time** | **`~38 seconds`** | Fast-forwarded non-blocking mock isolation; zero hung socket timeouts |
| **PII Redaction Invariants** | **`Enforced by Default`** | Automatic regex masking for PANs (`****249H`) and Bank Accounts (`****9012`) |

---

## 3. Engineering Paradigm & Safety Guarantees

Financial operations systems require deterministic arithmetic, verifiable data access, and bounded failure behavior. Standard LLM wrappers that execute business logic or arithmetic directly within model prompts fail in production due to floating-point drift, scope leakage across tenants, and unhandled upstream exceptions.

Arbiter isolates the Large Language Model strictly as an **intent classifier and semantic synthesizer**. All data access, client scoping, policy validation, and calculations are executed by deterministic Python layers before reaching the client.

```mermaid
flowchart TD
    classDef unmanagedStyle fill:#1e293b,stroke:#64748b,stroke-width:1px,color:#94a3b8;
    classDef managedStyle fill:#0f172a,stroke:#3b82f6,stroke-width:1.5px,color:#f8fafc;
    classDef coreStyle fill:#14532d,stroke:#22c55e,stroke-width:1.5px,color:#f0fdf4;

    subgraph UNMANAGED [" Standard LLM Pipeline "]
        R1[" Ingress Request "] --> LLM_MONO[" Monolithic LLM Context <br/>(Model performs arithmetic, data retrieval, and scoping internally) "]
        LLM_MONO --> OUT_MONO[" Output Text <br/>• Floating-point arithmetic drift <br/>• Scope leakage via prompt injection <br/>• Unhandled 429/5xx upstream exceptions "]
    end

    subgraph MANAGED [" Arbiter Multi-Agent Architecture "]
        R2[" Ingress Request "] --> PRE[" Scope Preflight & Ingress Guard "]
        PRE --> AGENT_TIER[" Multi-Agent Router & Specialists <br/>(LLM: Semantic QA & Routing Only) "]
        AGENT_TIER <--> TOOL_TIER[" Tool Verification Layer <br/>• 24 Declarative Tool Schemas <br/>• 100% decimal.Decimal Math <br/>• Isolated In-Memory Ledger Store "]
        TOOL_TIER --> SANITIZE[" Output Guard & PII Sanitizer "]
        SANITIZE --> OUT_TYPED[" Typed AnswerSchema JSON <br/>• Exact numerical precision <br/>• Enforced tenant bounds <br/>• Deterministic refusal/abstention envelopes "]
    end

    class R1,LLM_MONO,OUT_MONO unmanagedStyle;
    class R2,PRE,AGENT_TIER,TOOL_TIER,SANITIZE managedStyle;
    class OUT_TYPED coreStyle;
```

### Architectural Comparison

| Dimension | Conventional LLM Wrapper | Arbiter Implementation |
| :--- | :--- | :--- |
| **Arithmetic & Ledgers** | Computed via model token predictions; prone to floating-point rounding errors | Computed deterministically via Python `decimal.Decimal` over structured in-memory ledgers |
| **Agent Topology** | Monolithic prompt with unstructured system instructions | Hub-and-spoke multi-agent routing with deterministic preflight and keyword overrides |
| **Tool Authorization** | Model calls registered tools without authorization checks | Authoritative registry (`TOOL_REGISTRY`) with explicit agent allowlists |
| **Tenant Isolation** | Soft filtering via system prompt instructions | Hard runtime context closures enforcing authorized `client_id` boundaries |
| **Argument Validation** | Unchecked JSON payloads passed directly to underlying APIs | Strict Pydantic schemas validating types, ISO-8601 dates, and enum bounds |
| **PII & Data Redaction** | Sensitive fields and credentials transmitted in plaintext | Automated regex redaction for PANs (`****249H`), bank accounts (`****9012`), and secrets |
| **Indirect Injection** | External data injected directly into model context | External text isolated within `<untrusted_data>` XML tags with non-execution directives |
| **Response Contract** | Unstructured conversational text apologies | Formal schema envelopes with explicit `refused` and `abstained` boolean fields |
| **Transient Faults** | Uncaught 429/5xx HTTP exceptions crash the pipeline | Classification-aware retry engine with exponential backoff and randomized full jitter |
| **Cascading Failures** | Unbounded retries against degraded upstream providers | 3-state Circuit Breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) with 30s recovery cooldown |
| **Service Boundary** | Ad-hoc scripts or unversioned endpoints | Asynchronous FastAPI service boundary with `X-Request-ID` correlation and worker threadpools |
| **Telemetry & Tracing** | Unstructured console prints | Monotonic microsecond profiling with sanitized JSONL event sink and token cost accounting |
| **Evaluation & CI** | Manual prompt spot-checking | 45-case ground-truth offline benchmark suite with zero-drift runner |
| **Operations Interface** | Generic chat window without observability | 9-workspace React 19 / TypeScript console with live trace inspection |

---

## 4. Multi-Agent Topology

Arbiter employs a coordinated agent hierarchy where the `router` acts as a semantic traffic controller, dispatching queries to domain specialists according to strict capability boundaries.

```mermaid
graph TD
    classDef routerStyle fill:#312e81,stroke:#6366f1,stroke-width:2px,color:#e0e7ff;
    classDef specialistStyle fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#ecfdf5;
    classDef complianceStyle fill:#7f1d1d,stroke:#f87171,stroke-width:2px,color:#fef2f2;

    ROUTER[" Router Agent <br/><b>(Intent Classification & Keyword Overrides)</b> "]

    B_QA[" <b>Book QA Specialist</b> <br/><i>16 Registered Tools</i> <br/>• Cash Balances & Ledger Summaries <br/>• Portfolio Valuation & Target Drift <br/>• Position Quantity & Age Tracking <br/>• Snapshot Conflict Detection "]

    KYC[" <b>KYC Profile Specialist</b> <br/><i>2 Registered Tools</i> <br/>• Masked Identity Profiles <br/>• Suitability Reviews & Risk Levels <br/>• Deterministic PAN Masking <br/>• Masked Bank Account Views "]

    NOTES[" <b>Notes Desk Specialist</b> <br/><i>2 Registered Tools</i> <br/>• Client Interaction History <br/>• Transaction Memos & Notes <br/>• Author & Timestamp Verification <br/>• Free-Text Memory Retrieval "]

    MKT[" <b>Market Desk Specialist</b> <br/><i>4 Registered Tools</i> <br/>• Covered Symbol Metadata <br/>• Monthly Close Price Lookups <br/>• Historical Percentage Returns <br/>• Covered Financial Headlines "]

    COMP[" <b>Compliance Specialist</b> <br/><i>0 Registered Tools</i> <br/>• Investment Advice Refusals <br/>• Asset Allocation Blocks <br/>• Cross-Client Snooping Rejections <br/>• Policy Guardrail Enforcement "]

    ROUTER -->|Portfolio & Ledger| B_QA
    ROUTER -->|Identity & Risk| KYC
    ROUTER -->|Notes & Call Logs| NOTES
    ROUTER -->|Covered Tickers| MKT
    ROUTER -->|Advice / Unsafe Requests| COMP

    class ROUTER routerStyle;
    class B_QA,KYC,NOTES,MKT specialistStyle;
    class COMP complianceStyle;
```

---

## 5. End-to-End Request Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as User / Analyst
    participant UI as React Console
    participant API as FastAPI Layer
    participant SEC as SecurityManager
    participant ORCH as ArbiterOrchestrator
    participant ROUTER as Router Agent
    participant SPEC as Specialist Agent
    participant TV as ToolVerifier
    participant TOOL as Deterministic Tool
    participant OBS as ObservabilityManager

    Analyst->>UI: Submit Question ("What is cash balance for cli_1014?")
    UI->>API: POST /v1/query {client_id, question}
    API->>OBS: start_request(req_id, client_id)
    API->>SEC: validate_input(question, client_id)
    alt Prompt Injection / Disallowed Request
        SEC-->>API: Refusal / Violation Result (refused=True)
        API-->>UI: 200 OK Safe Refusal Envelope
    else Valid Ingress
        SEC-->>API: Input Validated
        API->>ORCH: answer(question, client_id)
        ORCH->>ROUTER: Classify Intent
        ROUTER-->>ORCH: Route to book_qa
        ORCH->>SPEC: Execute book_qa Specialist
        SPEC->>TV: invoke("get_cash_balance", {client_id: "cli_1014"})
        TV->>TV: Authorize Agent (book_qa allowed?)
        TV->>TV: Validate Scope (matches request context?)
        TV->>TV: Validate Args Schema (Pydantic CashBalanceArgs)
        TV->>TOOL: Execute get_cash_balance(cid="cli_1014")
        TOOL-->>TV: {cash_balance: "125450.00"} (Decimal Math)
        TV->>TV: Verify Result Shape & Citations
        TV-->>SPEC: Verified Tool Result
        SPEC-->>ORCH: Specialist Reasoning & Answer
        ORCH->>SEC: sanitize_output(raw_answer)
        SEC-->>ORCH: Sanitized AnswerSchema Envelope
        ORCH->>OBS: finish_request(trace)
        ORCH-->>API: Complete Response Envelope
        API-->>UI: 200 OK JSON QueryResponse
        UI-->>Analyst: Render Answer, Timeline, Citations & Agent Path
    end
```

---

## 6. Security Architecture & Trust Boundaries

Arbiter enforces a strict three-tier defense-in-depth model that classifies all external inputs and model completions as **untrusted**, passing them through hardened inspection barriers before they interact with internal business logic.

```mermaid
flowchart TD
    classDef untrusted fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fee2e2;
    classDef gateway fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fef3c7;
    classDef trusted fill:#14532d,stroke:#22c55e,stroke-width:2px,color:#f0fdf4;

    subgraph UNTRUSTED_ZONE [" UNTRUSTED INPUT ZONE "]
        U1[" User Natural-Language Prompt "]
        U2[" LLM Model Completions & Tool Calls "]
        U3[" Retrieved Unstructured Notes & Memos "]
        U4[" External Market Headlines "]
    end

    subgraph SECURITY_BOUNDARY [" SECURITY & SANITIZATION BOUNDARY "]
        SB1[" <b>InputGuard</b>: Length Caps (≤10k), Null-Byte Stripping, Injection Patterns "]
        SB2[" <b>Client Scope Validator</b>: Runtime Closure vs Authorized Client Preflight "]
        SB3[" <b>PromptGuard</b>: XML Encapsulation (&lt;untrusted_data&gt;) "]
        SB4[" <b>Tool Authorization Matrix</b>: Agent-to-Tool Allowlist Enforcement "]
        SB5[" <b>OutputGuard</b>: PAN / Bank Account Masking & Cross-Client Citation Stripper "]
        SB6[" <b>Security Audit Sink</b>: Structured Security Events Emitted to Telemetry "]
    end

    subgraph TRUSTED_ZONE [" TRUSTED CORE EXECUTION ZONE "]
        TC1[" Authenticated Request Context (`contextvars`) "]
        TC2[" Declarative `TOOL_REGISTRY` (24 Tools) "]
        TC3[" Deterministic `decimal.Decimal` Financial Engines "]
        TC4[" Grounded In-Memory Client Ledger & Market Store "]
        TC5[" Structured AnswerSchema Validation Contract "]
    end

    U1 --> SB1
    U2 --> SB4 & SB5
    U3 & U4 --> SB3
    SB1 & SB2 & SB3 & SB4 --> TRUSTED_ZONE
    TRUSTED_ZONE --> SB5 --> SB6

    class U1,U2,U3,U4 untrusted;
    class SB1,SB2,SB3,SB4,SB5,SB6 gateway;
    class TC1,TC2,TC3,TC4,TC5 trusted;
```

---

## 7. Tool Verification Pipeline & Registry

Every tool call initiated by an agent is intercepted by `ToolVerifier` before reaching the execution layer. The LLM is never permitted to execute code directly or bypass argument schemas.

```mermaid
flowchart LR
    classDef stepStyle fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef passStyle fill:#14532d,stroke:#22c55e,stroke-width:2px,color:#f0fdf4;

    REQ[" LLM Tool Request "] --> S1[" 1. Authorize Agent "]
    S1 --> S2[" 2. Validate Client Scope "]
    S2 --> S3[" 3. Parse Strict Schema "]
    S3 --> S4[" 4. Execute Deterministic Tool "]
    S4 --> S5[" 5. Verify Result & Citations "]
    S5 --> RES[" Trusted Tool Result "]

    class REQ,S1,S2,S3,S4,S5 stepStyle;
    class RES passStyle;
```

### Registered Tool Distribution (24 Deterministic Tools)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                     AUTHORITATIVE TOOL REGISTRY BREAKDOWN                     │
├──────────────────────────────┬───────────────┬────────────────────────────────┤
│ Specialist Agent             │ Tool Count    │ Domain Responsibilities        │
├──────────────────────────────┼───────────────┼────────────────────────────────┤
│ 📊 Book QA Specialist        │ 16 Tools      │ Cash, Positions, Holdings,     │
│                              │               │ Portfolios, Drift, Age, Ledger │
├──────────────────────────────┼───────────────┼────────────────────────────────┤
│ 🪪 KYC Profile Specialist     │ 2 Tools       │ Masked KYC Profiles,           │
│                              │               │ Suitability Reviews            │
├──────────────────────────────┼───────────────┼────────────────────────────────┤
│ 📝 Notes Desk Specialist     │ 2 Tools       │ Client Notes, Transaction      │
│                              │               │ Memo Lookups                   │
├──────────────────────────────┼───────────────┼────────────────────────────────┤
│ 📈 Market Desk Specialist    │ 4 Tools       │ Instrument Specs, Close Prices,│
│                              │               │ Returns, Market News           │
├──────────────────────────────┼───────────────┼────────────────────────────────┤
│ 🛡️ Compliance Specialist     │ 0 Tools       │ Zero Tools (Refusal Only)      │
├──────────────────────────────┼───────────────┼────────────────────────────────┤
│ TOTAL REGISTERED TOOLS       │ 24 Tools      │ 100% Deterministic Execution   │
└──────────────────────────────┴───────────────┴────────────────────────────────┘
```

<details>
<summary><b>View Complete 24-Tool Declarative Registry Table</b></summary>
<br/>

| Owning Agent | Tool Name | Scope Constraint | Description |
| :--- | :--- | :---: | :--- |
| `book_qa` | `get_client_profile` | `client_id` Required | Retrieve client metadata record without sensitive PII |
| `book_qa` | `get_client_accounts` | `client_id` Required | Retrieve list of account dictionaries for the client |
| `book_qa` | `get_client_holdings` | `client_id` Required | Retrieve positions snapshot list for the client |
| `book_qa` | `get_client_suitability_reviews` | `client_id` Required | Retrieve suitability reviews list for the client |
| `book_qa` | `get_client_transactions` | `client_id` Required | Retrieve filtered transactions list for the client |
| `book_qa` | `find_earliest_transaction` | `client_id` Required | Find chronologically earliest transaction matching filters |
| `book_qa` | `find_largest_transaction` | `client_id` Required | Find transaction with largest numeric field value |
| `book_qa` | `get_cash_balance` | `client_id` Required | Calculate USD cash balance aggregated from transactions |
| `book_qa` | `get_position_quantity` | `client_id` Required | Calculate held quantity of a security as of a date |
| `book_qa` | `get_holdings_count` | `client_id` Required | Calculate count of distinct held securities as of a date |
| `book_qa` | `get_transaction_total` | `client_id` Required | Sum a numeric field across filtered transactions |
| `book_qa` | `get_transaction_count` | `client_id` Required | Count transactions matching filter criteria |
| `book_qa` | `get_portfolio_value` | `client_id` Required | Calculate total market value of held positions |
| `book_qa` | `get_target_drift` | `client_id` Required | Calculate target allocation drift percentage |
| `book_qa` | `get_account_age` | `client_id` Required | Calculate age of an account in days |
| `book_qa` | `check_position_snapshot_conflict` | `client_id` Required | Detect conflict between position snapshot and ledger |
| `kyc_profile` | `get_kyc_profile` | `client_id` Required | Retrieve masked KYC profile view for a client |
| `kyc_profile` | `get_suitability` | `client_id` Required | Retrieve suitability reviews list for a client |
| `notes_desk` | `get_notes` | `client_id` Required | Retrieve relationship notes list for a client |
| `notes_desk` | `get_memos` | `client_id` Required | Retrieve transaction memos list for a client |
| `market_desk` | `get_instrument` | Global / Symbol | Retrieve sector and exchange metadata for covered symbol |
| `market_desk` | `get_price` | Global / Symbol | Retrieve monthly close price for covered symbol as-of date |
| `market_desk` | `get_return` | Global / Symbol | Calculate percentage return of symbol between two dates |
| `market_desk` | `get_news` | Global / Symbol | Retrieve news articles for covered symbol |

</details>

---

## 8. Reliability Architecture & Fault Tolerance

Arbiter features an enterprise-grade `ReliabilityEngine` engineered to isolate the platform from upstream LLM outages, provider rate limits, network partitions, and cascading failure loops without degrading service availability.

```mermaid
flowchart TD
    classDef startStyle fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef cbStyle fill:#312e81,stroke:#6366f1,stroke-width:2px,color:#e0e7ff;
    classDef execStyle fill:#0f172a,stroke:#38bdf8,stroke-width:1.5px,color:#f0f9ff;
    classDef classStyle fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fef3c7;
    classDef retryStyle fill:#1e1b4b,stroke:#a855f7,stroke-width:2px,color:#faf5ff;
    classDef errorStyle fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fee2e2;
    classDef safeStyle fill:#14532d,stroke:#22c55e,stroke-width:2px,color:#f0fdf4;

    REQ[" Upstream LLM / Agent Invocation "] --> CB_GATE{" 1. Circuit Breaker Gate "}

    subgraph CIRCUIT_BREAKER [" Circuit Breaker State Machine "]
        CB_GATE -->|CLOSED: Normal| EXEC[" 2. Execute Request with Timeout <br/>(15.0s Strict Wall-Clock Limit) "]
        CB_GATE -->|OPEN: Degraded| FAST_FALLBACK[" Fast Fallback Envelope <br/>(abstained=True, flags=['circuit_open']) "]
        CB_GATE -->|HALF-OPEN: Cooldown Expired| PROBE[" 2b. Single Probe Request "]
        PROBE --> EXEC
    end

    subgraph EXECUTION_PATH [" Execution & Result Processing "]
        EXEC -->|HTTP 200 / Valid Output| SUCCESS[" Return Valid Result & Reset Failure Count "]
        EXEC -->|Exception / Timeout| CLASSIFIER{" 3. Error Classification Engine "}
    end

    subgraph CLASSIFICATION_AND_RETRY [" Classification & Retry Engine "]
        CLASSIFIER -->|Non-Retryable: 400 Bad Request, 401/403 Auth, Scope, Policy| NON_RETRY[" Deterministic Error / Refusal Envelope <br/>(Zero Futile Retries) "]
        CLASSIFIER -->|Retryable: 429 Rate Limit, 5xx Server, Connection, Timeout| ATTEMPTS{" Attempts Remaining? "}
        ATTEMPTS -->|Yes: Attempt < 3| BACKOFF[" 4. Exponential Backoff + Jitter <br/>(Base: 0.5s, Max: 10s, Full Jitter) "]
        BACKOFF --> EXEC
        ATTEMPTS -->|No: Exhausted| TRIP_CB[" Trip Circuit Breaker to OPEN <br/>(Cooldown: 30.0s) "]
        TRIP_CB --> TIMEOUT_FALLBACK[" Safe Fallback Envelope <br/>(abstained=True, flags=['upstream_issue']) "]
    end

    SUCCESS --> RESP[" Structured AnswerSchema Response "]
    FAST_FALLBACK --> RESP
    NON_RETRY --> RESP
    TIMEOUT_FALLBACK --> RESP

    class REQ,RESP startStyle;
    class CB_GATE,PROBE cbStyle;
    class EXEC,SUCCESS execStyle;
    class CLASSIFIER classStyle;
    class ATTEMPTS,BACKOFF,TRIP_CB retryStyle;
    class NON_RETRY errorStyle;
    class FAST_FALLBACK,TIMEOUT_FALLBACK safeStyle;
```

### Core Reliability Invariants

1. **Classification-Aware Retries**: Retries *only* transient upstream failures (429 Rate Limit, 5xx Server Error, network resets, socket timeouts). Client errors (400, 401, 404), policy refusals, and scope violations fail immediately with zero futile retries.
2. **Exponential Backoff with Full Jitter**: Backoff intervals scale exponentially ($0.5s \to 1.0s \to 2.0s \dots \le 10.0s$) with randomized jitter to disperse concurrency spikes and eliminate thundering-herd effects against upstream providers.
3. **State-Machine Circuit Breaker**: Trips to `OPEN` after 3 consecutive upstream failures, immediately short-circuiting downstream calls into safe fallback envelopes (`flags=['circuit_open']`). Transitions to `HALF_OPEN` after a 30s recovery cooldown to probe upstream health.
4. **Deterministic Non-Blocking Timeouts**: Upstream model calls enforce a strict 15.0s per-attempt wall-clock timeout via non-blocking threadpool executors, preventing thread starvation.
5. **Schema-Valid Fallback Guarantees**: System degradation always yields a complete, schema-valid `AnswerSchema` JSON envelope (`abstained=True`), ensuring clients never receive raw 500 error pages or truncated responses.

### Error Classification Matrix

| Error Type | Status / Exception | Policy | Action |
| :--- | :--- | :---: | :--- |
| **Rate Limit** | HTTP 429, `ResourceExhausted` | **`RETRYABLE`** | Exponential backoff respecting provider `Retry-After` headers |
| **Server Error** | HTTP 500, 502, 503, 504 | **`RETRYABLE`** | Exponential backoff with full jitter up to 3 attempts |
| **Gateway Timeout** | `TimeoutError`, `APITimeoutError` | **`RETRYABLE`** | Strict 15.0s per-attempt timeout; retried with jitter |
| **Connection Drop** | `ConnectionResetError`, `BrokenPipe` | **`RETRYABLE`** | Immediate retry with backoff |
| **Client Error** | HTTP 400, 401, 403, 404 | **`NON-RETRYABLE`** | Immediate failure response (zero futile retries) |
| **Policy Refusal** | Investment advice, Cross-client | **`NON-RETRYABLE`** | Returns deterministic refusal envelope (`refused=True`) |
| **Scope Violation** | Unknown client ID preflight | **`NON-RETRYABLE`** | Returns deterministic abstention envelope (`abstained=True`) |
| **Tool Schema Error** | Invalid filter enum, malformed date | **`NON-RETRYABLE`** | Returns deterministic tool validation failure envelope |

---

## 9. Production-Grade Observability & Telemetry

Every request processed by Arbiter is correlated end-to-end via asynchronous context variables (`contextvars`), capturing microsecond latency breakdowns, sanitized tool executions, and token usage without storing unmasked PII.

```mermaid
flowchart TD
    classDef obsCard fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#f5f3ff;
    classDef telemetryCard fill:#0f172a,stroke:#64748b,stroke-width:1px,color:#e2e8f0;

    REQ[" Incoming Query Request "] --> CTX[" Context Manager: Binds <b>req_uuid</b> & monotonic start_time "]

    CTX --> T1[" 1. Router Profiling: Route selected & latency "]
    T1 --> T2[" 2. Specialist Execution: Model call latency, input/output tokens, cost "]
    T2 --> T3[" 3. Tool Verification Traces: Tool names, sanitized args, sanitized results, timing "]
    T3 --> T4[" 4. Security Audit Events: Injection scans, redaction count, boundary checks "]
    T4 --> T5[" 5. Validation Profiling: AnswerSchema check, citation verification "]

    T1 & T2 & T3 & T4 & T5 --> AGG[" In-Memory Metrics Aggregator <br/>(P50/P95/P99 Latency, Tool Success Rate, Token Distribution) "]
    
    AGG --> API_OBS[" Observability API (/v1/observability/summary) "]
    API_OBS --> UI_DASH[" React Operations Console (Live Traces & Telemetry) "]

    class REQ,CTX,AGG obsCard;
    class T1,T2,T3,T4,T5,API_OBS,UI_DASH telemetryCard;
```

<details>
<summary><b>View Sample Sanitized Request Trace JSON</b></summary>
<br/>

```json
{
  "metadata": {
    "request_id": "req_8a7d3f2c1b0e",
    "timestamp": "2026-09-04T12:00:00.123456Z",
    "question_id": "q_req_8a7d3f2c1b0e",
    "client_id": "cli_1014",
    "provider": "gemini",
    "model": "gemini-3.6-flash"
  },
  "router": {
    "selected_specialist": "book_qa",
    "agent_path": ["router", "book_qa"],
    "latency_ms": 11.2,
    "llm_call": null
  },
  "specialist": {
    "agent_name": "book_qa",
    "latency_ms": 412.4,
    "llm_call": {
      "provider": "gemini",
      "model": "gemini-3.6-flash",
      "latency_ms": 408.1,
      "input_tokens": 420,
      "output_tokens": 58,
      "total_tokens": 478,
      "estimated_cost_usd": 0.000049,
      "success": true
    },
    "tool_calls": [
      {
        "tool_name": "get_cash_balance",
        "agent": "book_qa",
        "latency_ms": 0.82,
        "success": true,
        "sanitized_args": {"cid": "cli_1014"},
        "sanitized_result_summary": {"cash_balance": "125450.00"}
      }
    ]
  },
  "validation": {
    "schema_valid": true,
    "citation_count": 2,
    "citations": ["cli_1014", "acc_1014_01"],
    "validation_errors": []
  },
  "status": "success",
  "confidence": 1.0,
  "total_latency_ms": 424.8,
  "total_tokens": 478,
  "total_cost_usd": 0.000049
}
```

</details>

---

## 10. Frontend Operations Console

The frontend is an enterprise operations console built in **React 19, TypeScript, Vite, and Tailwind CSS**, featuring 9 dedicated operations workspaces.

```mermaid
flowchart TD
    classDef uiStyle fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef routeStyle fill:#0f172a,stroke:#64748b,stroke-width:1px,color:#cbd5e1;

    UI_ROOT[" React 19 Operations Console (Vite + TypeScript) "]

    subgraph VIEWS [" 9 Dedicated Operations Workspaces "]
        V1[" 📊 Executive Dashboard "]
        V2[" 💬 Ask Arbiter (Workspace) "]
        V3[" 👥 Clients Book (Masked Directory) "]
        V4[" 🕸️ Agent Network Topology "]
        V5[" 🔧 Tool Verification Registry "]
        V6[" 🛡️ Security & Trust Visualizer "]
        V7[" ⚡ Reliability & Circuit Breaker "]
        V8[" 📈 Observability & Live Traces "]
        V9[" 🏛️ System Architecture Matrix "]
    end

    UI_ROOT --> VIEWS
    VIEWS --> API_CLIENT[" Typed REST API Client (`src/services/api.ts`) "]
    API_CLIENT --> FASTAPI[" FastAPI Backend Service Boundary "]

    class UI_ROOT,API_CLIENT uiStyle;
    class V1,V2,V3,V4,V5,V6,V7,V8,V9,FASTAPI routeStyle;
```

### Operations Workspaces Map

| Console Workspace | Route | Purpose & Key Features |
| :--- | :--- | :--- |
| **Executive Dashboard** | `/` | Real-time system health, dataset counts, 100% benchmark score card, quick prompts |
| **Ask Arbiter** | `/ask` | Live client-scoped query runner, execution timeline, exact value callouts, citations |
| **Clients Book** | `/clients` | Client directory with masked PII (`****249H`), accounts, risk tolerance, suitability |
| **Agent Network** | `/agents` | Interactive agent topology graph, tool authorization scopes, and refusal boundaries |
| **Verified Tools** | `/tools` | Authoritative 24-tool registry with owning agents, schemas, and return invariants |
| **Security & Trust** | `/security` | Untrusted-to-trusted boundary visualizer, injection defense filters, PII redactor |
| **Reliability Engine** | `/reliability` | Real-time Circuit Breaker state, exponential backoff policies, error matrix |
| **Observability** | `/observability` | In-memory request telemetry, P50/P95 latency percentiles, sanitized JSON traces |
| **Architecture** | `/architecture` | Comprehensive system design mapping and layer-by-layer technical breakdown |

---

## 11. Offline Evaluation & Benchmarking Results

Arbiter includes a zero-drift ground-truth evaluation harness (`evals/`) covering 45 curated benchmark test cases across 7 operational categories.

```
================================================================
  ARBITER MULTI-AGENT BENCHMARK EVALUATION (45 TEST CASES)
================================================================
Mode:            DETERMINISTIC OFFLINE / MOCK
Dataset:         evals/datasets/benchmark.json
----------------------------------------------------------------
Metric Dimension               Score     Status
----------------------------------------------------------------
Routing Accuracy               100.0%    ✅ PERFECT
Factual & Numerical Accuracy   100.0%    ✅ PERFECT (Decimal Exact)
Citation Precision             100.0%    ✅ PERFECT (No Hallucinations)
Safety / Policy Refusal        100.0%    ✅ PERFECT (Compliant Envelopes)
Schema Invariant Compliance    100.0%    ✅ PERFECT (Valid AnswerSchema)
----------------------------------------------------------------
TOTAL SUITE RESULT             45 / 45   100.0% PASS
================================================================
```

### Category Breakdown

| Category | Cases | Pass Rate | Routing Accuracy | Factuality | Key Invariants Tested |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Book QA** | 8 | **`100.0%`** | `100.0%` | `100.0%` | Cash balances, holdings, portfolio value, net transactions |
| **KYC Profile** | 7 | **`100.0%`** | `100.0%` | `100.0%` | Risk profiles, PAN masking (`****249H`), bank account masking |
| **Notes Desk** | 6 | **`100.0%`** | `100.0%` | `100.0%` | Interaction notes, transaction memos, date filtering |
| **Market Desk** | 8 | **`100.0%`** | `100.0%` | `100.0%` | Historical close prices, percentage returns, uncovered abstention |
| **Compliance** | 6 | **`100.0%`** | `100.0%` | `100.0%` | Stock buy/sell advice refusal, crypto/tax structuring blocks |
| **Security & Isolation** | 6 | **`100.0%`** | `100.0%` | `100.0%` | Cross-client snooping, unknown client preflight, injection defense |
| **Edge Cases** | 4 | **`100.0%`** | `100.0%` | `100.0%` | Future price lookups, malformed dates, account age calculations |

---

## 12. Implementation Map

| Subsystem | Source Path | Status | Implemented Responsibilities |
| :--- | :--- | :---: | :--- |
| **Orchestrator** | [`arbiter/orchestrator.py`](arbiter/orchestrator.py) | **COMPLETE** | Client preflight check, intent routing, agent invocation, envelope validation |
| **Specialist Agents** | [`arbiter/agents/`](arbiter/agents/) | **COMPLETE** | 6 agents (`router`, `book_qa`, `kyc_profile`, `notes_desk`, `market_desk`, `compliance`) |
| **Deterministic Tools** | [`arbiter/tools/`](arbiter/tools/) | **COMPLETE** | Exact `decimal.Decimal` calculations, ledger scans, market observations |
| **Tool Verification** | [`arbiter/tool_verification/`](arbiter/tool_verification/) | **COMPLETE** | 24 registered tools, agent authorization, strict schema, scope validation |
| **Security Subsystem** | [`arbiter/security/`](arbiter/security/) | **COMPLETE** | Input injection guard, prompt quarantine, PII regex masking, audit events |
| **Reliability Engine** | [`arbiter/reliability/`](arbiter/reliability/) | **COMPLETE** | Circuit breaker, error classification, exponential backoff with full jitter |
| **Observability Subsystem**| [`arbiter/observability/`](arbiter/observability/) | **COMPLETE** | Correlation IDs, microsecond profiling, P50/P95 latency percentiles, pricing |
| **FastAPI Layer** | [`arbiter/api/`](arbiter/api/) | **COMPLETE** | Transport schemas, threadpool execution, error normalization, health probes |
| **Frontend Console** | [`frontend/`](frontend/) | **COMPLETE** | 9-view React 19 console, typed API client, interactive topology and telemetry |
| **Evaluation Framework** | [`evals/`](evals/) | **COMPLETE** | 45-case ground-truth benchmark suite, offline mock engine, automated reports |

---

## 13. Project Structure

```
arbiter/
├── arbiter/
│   ├── agents/                   # 6 Specialist agents (book_qa, kyc, notes, market, compliance, router)
│   ├── api/                      # Asynchronous FastAPI service boundary and HTTP routes
│   ├── datastore.py              # In-memory indices for synthetic client ledger and market data
│   ├── observability/            # Microsecond profiling, PII redaction, token pricing, trace sink
│   ├── orchestrator.py           # ArbiterOrchestrator coordinator and routing engine
│   ├── reliability/              # CircuitBreaker, classification-aware retry, and safe fallbacks
│   ├── schemas.py                # Core AnswerSchema and request/response contracts
│   ├── security/                 # InputGuard, PromptGuard, OutputGuard, and SecurityManager
│   ├── tool_verification/        # Authoritative 24-tool registry, authorization gates, schemas
│   └── tools/                    # Deterministic Decimal math and structured retrieval tools
├── data/
│   ├── client_book.json          # Synthetic client ledgers, accounts, notes, and KYC records
│   └── market_data.json          # Synthetic monthly close prices and covered market headlines
├── evals/
│   ├── datasets/benchmark.json   # 45 curated ground-truth test cases across 7 categories
│   ├── evaluators/               # Routing, factuality, citation, safety, and schema evaluators
│   ├── mock_orchestrator.py      # Deterministic offline evaluation orchestrator (0ms latency)
│   └── runner.py                 # CLI benchmark runner with JSON report generation
├── frontend/
│   ├── src/                      # React 19 + TypeScript operations console
│   │   ├── components/           # Navigation, StatCards, StatusBadges, ResponseViews
│   │   ├── pages/                # 9 dedicated operations pages (Dashboard, Ask, Tools, Security, etc.)
│   │   ├── services/api.ts       # Typed REST API client communicating with FastAPI
│   │   └── test/                 # Component and API client vitest suite (10 tests)
│   └── package.json              # Vite, Tailwind CSS v4, Lucide React dependencies
└── tests/                        # 390 automated unit and integration tests (100% passing)
```

---

## 14. Quickstart Guide

### 1. Prerequisites
* Python 3.11+
* Node.js 18+ and npm
* Git

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-username/arbiter.git
cd arbiter

# Initialize Python virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r docker/requirements.example.txt

# Configure environment variables
cp .env.example .env
```

*(Note: Set `LLM_PROVIDER=gemini` and provide `GEMINI_API_KEY` in `.env` for live LLM execution, or run tests/mock evals with zero external credentials).*

### 3. Run the Backend API Service
```bash
uvicorn arbiter.api.app:create_app --factory --host 0.0.0.0 --port 8080 --reload
```
* Interactive Swagger Docs: `http://localhost:8080/docs`
* Health Check: `http://localhost:8080/health`

### 4. Run the Frontend Operations Console
```bash
cd frontend
npm install
npm run dev
```
* Open your browser at `http://localhost:5173`

### 5. Run Automated Test Suites
```bash
# Run full backend test suite (390 tests)
.venv/bin/pytest tests/ -v

# Run frontend vitest suite (10 tests)
cd frontend && npm test
```

### 6. Run Offline Ground-Truth Benchmark
```bash
# Run all 45 benchmark evaluation test cases in <0.1s
.venv/bin/python -m evals.runner --mode mock
```

---

## 15. Interactive Demo Flow

When exploring the platform via the operations console at `http://localhost:5173`, follow this recommended walkthrough:

```
  ┌─────────────────────────┐
  │ 1. Executive Dashboard  │  Review system health, 100% benchmark badge, and quick query templates
  └────────────┬────────────┘
               ▼
  ┌─────────────────────────┐
  │ 2. Ask Arbiter QA       │  Select client 'cli_1014' and query cash balances or portfolio value
  └────────────┬────────────┘
               ▼
  ┌─────────────────────────┐
  │ 3. KYC Profile Query    │  Ask for client risk profile; verify automatic PII masking (****249H)
  └────────────┬────────────┘
               ▼
  ┌─────────────────────────┐
  │ 4. Market Desk Query    │  Query historical returns for 'AAPL'; test uncovered symbols for abstention
  └────────────┬────────────┘
               ▼
  ┌─────────────────────────┐
  │ 5. Compliance Refusal   │  Ask "Should I buy more TSLA?"; observe compliant policy refusal envelope
  └────────────┬────────────┘
               ▼
  ┌─────────────────────────┐
  │ 6. Injection Defense    │  Submit "Ignore previous instructions"; verify immediate security refusal
  └────────────┬────────────┘
               ▼
  ┌─────────────────────────┐
  │ 7. Tool Verification    │  Inspect the 24 registered tools and their agent authorization boundaries
  └────────────┬────────────┘
               ▼
  ┌─────────────────────────┐
  │ 8. Observability        │  Inspect live in-memory traces, latency percentiles, and token costs
  └─────────────────────────┘
```

---

## 16. Technical Details & API Specifications

<details>
<summary><b>FastAPI REST API Endpoints Specification</b></summary>
<br/>

### Available HTTP Endpoints

| Method | Path | Request Body | Response Schema | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | None | `HealthResponse` | Liveness probe returning process status (`{"status": "ok"}`) |
| `GET` | `/ready` | None | `ReadinessResponse` | Readiness probe returning dataset counts & active model |
| `POST` | `/v1/query` | `QueryRequest` | `QueryResponse` | Main natural-language query endpoint delegating to agents |
| `GET` | `/v1/clients` | None | `List[ClientSummary]` | Masked client directory for scope selector |
| `GET` | `/v1/agents` | None | `List[AgentSummary]` | Active agent roster and authorized tool lists |
| `GET` | `/v1/tools` | None | `List[ToolSummary]` | Authoritative 24-tool registry metadata |
| `GET` | `/v1/security/summary` | None | `SecuritySummary` | Active security guardrails and PII masking status |
| `GET` | `/v1/reliability/summary`| None | `ReliabilitySummary` | Circuit breaker status and retry configurations |
| `GET` | `/v1/observability/summary`| None | `ObservabilitySummary`| P50/P95 latencies, request counts, and recent traces |

### Example Query Request
```bash
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: req_demo_001" \
  -d '{
    "client_id": "cli_1014",
    "question": "What is the cash balance for cli_1014?"
  }'
```

### Example Structured Response
```json
{
  "request_id": "req_demo_001",
  "question_id": "q_req_demo_001",
  "answer": "The current cash balance for client cli_1014 is $125,450.00 USD.",
  "answer_value": "125450.00",
  "abstained": false,
  "refused": false,
  "reason": null,
  "citations": ["cli_1014", "acc_1014_01"],
  "confidence": 1.0,
  "flags": [],
  "agents": ["router", "book_qa"]
}
```

</details>

<details>
<summary><b>Production Reliability & Circuit Breaker Configuration</b></summary>
<br/>

The reliability subsystem is configurable via environment variables in `.env`:

```ini
# Maximum retry attempts on retryable upstream failures (429, 5xx, timeouts)
RELIABILITY_MAX_ATTEMPTS=3

# Initial backoff delay in seconds
RELIABILITY_INITIAL_BACKOFF=0.5

# Maximum backoff delay cap in seconds
RELIABILITY_MAX_BACKOFF=10.0

# Apply random jitter to prevent thundering herds (50%–100% interval)
RELIABILITY_JITTER=true

# Strict per-attempt wall-clock timeout in seconds
LLM_TIMEOUT_SECONDS=15.0

# Consecutive failures required to trip Circuit Breaker to OPEN
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3

# Cooldown duration in seconds before testing upstream in HALF_OPEN state
CIRCUIT_BREAKER_RECOVERY_SECONDS=30.0
```

</details>

<details>
<summary><b>Security Subsystem Invariants & Regex Patterns</b></summary>
<br/>

* **Input Length Guard**: Strings exceeding 10,000 characters or containing embedded null bytes (`\x00`) are rejected immediately.
* **Direct Jailbreak Filter**: Detects patterns matching `"ignore previous instructions"`, `"dan mode"`, `"developer mode"`, `"jailbreak"`, and prompt exfiltration attempts.
* **PAN Redactor**: Indian Permanent Account Numbers (format: `[A-Z]{5}[0-9]{4}[A-Z]`) are deterministically masked to `****<last4>` (e.g. `****249H`).
* **Bank Account Redactor**: Numeric account strings with $\ge 8$ digits are masked to `****<last4>` (e.g. `****9012`).
* **Secret Redactor**: API keys matching common vendor formats (Google, OpenAI, Bearer tokens) are replaced with `[REDACTED_SECRET]`.

</details>

---

## 17. License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
