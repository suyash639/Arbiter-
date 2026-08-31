# Arbiter

Arbiter is an Agentic Financial Operations & Intelligence Engine built using FastAPI and Agno. It is designed to act as a secure, back-office financial assistant that retrieves client profile details, transaction history, relationship notes, and market statistics from structured, synthetic client books and market feeds.

By separating reasoning orchestration from deterministic data calculations, Arbiter ensures exact financial accuracy, absolute client-scoping safety, and strict compliance boundaries.

---

## What is Arbiter?
Arbiter is a multi-agent financial intelligence engine designed to answer complex back-office questions regarding client data and market performance. Instead of allowing Large Language Models (LLMs) to perform arithmetic or cross-client lookups directly (which lead to hallucinations, floating-point errors, and PII leaks), Arbiter wraps a set of deterministic Python tools inside specialist agents. The LLM acts purely as a semantic router and synthesizer, while Python handles all retrieval, scoping, masking, and arithmetic.

---

## Problem It Solves
1. **Financial Precision**: Floating-point math is notoriously unreliable in LLMs. Arbiter uses Python's `decimal.Decimal` library within deterministic tools to guarantee exact, penny-perfect calculations.
2. **PII and Data Security**: Raw client PANs, bank accounts, and sensitive details must never leak into raw model contexts or exception logs. Arbiter masks sensitive fields at the database boundary before they ever reach an agent.
3. **Authorized Client Scoping**: Questions are strictly bound to a single authorized `client_id`. Specialist tool closures validate the requested scope on every invocation, preventing prompt injection or cross-client data scanning.
4. **Investment Advice Boundary**: Compliance guidelines prohibit automated platforms from generating personalized strategy, asset allocation, or buy/sell suggestions. Arbiter identifies advice-seeking prompts and returns compliant policy refusals.

---

## Architecture
Arbiter's architecture follows a hub-and-spoke multi-agent system layout:

```
                          Incoming Request payload
                                     ↓
                          [ ArbiterOrchestrator ]
                                     ↓
                (Deterministic Pre-flight Scope Check)
                                     ↓
                       [ Router / Classifier Agent ]
                                     ↓
         ┌───────────────┬───────────┼───────────────┬───────────────┐
         ↓               ↓           ↓               ↓               ↓
    [ Book QA ]    [ KYC Profile ] [ Notes Desk ] [ Market Desk ] [ Compliance ]
         ↓               ↓           ↓               ↓               ↓
     Deterministic   Masked PII   Relationship  Covered Market    Safety Policy
      Book Tools     KYC Tools    Memos Tools     Data Tools        Refusals
         └───────────────┴───────────┴───────────────┴───────────────┘
                                     ↓
                          Structured AnswerSchema
                                     ↓
                              Response JSON
```

---

## How Request Routing Works
The `ArbiterOrchestrator` receives questions and classifies them using a router agent (backed by `valura-fast` model) combined with pre-LLM deterministic compliance keyword overrides.

| Request Type / Topic | Specialist Agent | Responsibility |
| --- | --- | --- |
| Portfolio, cash balance, holdings, transactions, cash calculations, portfolio value, drift, account age | `book_qa` | Performs client book retrieval and asset calculation. |
| KYC status, risk profile, PAN, bank account, DOB, address, income, employment details | `kyc_profile` | Retrieves client identity facts with deterministic masking. |
| Client notes, transaction descriptions, note dates, memos, author checks | `notes_desk` | Scans free-text notes and transaction memos for matching details. |
| Covered stocks details, sectors, monthly close price search, return calculations, covered market news | `market_desk` | Performs global market index lookup and news retrieval. |
| Out-of-scope requests, cross-client scope breaches, investment recommendations | `compliance` | Returns structured policy refusals. |

---

## Specialist Agents

### Book QA
* **Purpose**: Resolves mathematical questions concerning client securities, snapshots, cash deposits, and withdrawal transactions.
* **Tools**: `get_cash_balance`, `get_position_quantity`, `get_holdings_count`, `get_transaction_total`, `get_transaction_count`, `get_portfolio_value`, `get_target_drift`, `get_account_age`, `check_position_snapshot_conflict`.
* **Boundaries**: Strictly client-scoped; cannot access market indexes or KYC personal profiles.
* **Example**: "What is the cash balance for cli_1014?"

### KYC Profile
* **Purpose**: Manages personal client profile facts and identity verification.
* **Tools**: `get_client_kyc_profile`, `get_suitability_reviews`.
* **Boundaries**: All PAN and bank account values are masked deterministically. Raw client records are never exposed.
* **Example**: "What is cli_1014's KYC status and risk profile?"

### Notes Desk
* **Purpose**: Inspects client call logs, notes, and memo fields for specific transactional information.
* **Tools**: `get_client_notes`, `get_transaction_memos`.
* **Boundaries**: Exposes only text notes and transaction memos, keeping files secure.
* **Example**: "What notes are available for cli_1014?"

### Market Desk
* **Purpose**: Answers queries about stock close prices, monthly performance, and financial headlines.
* **Tools**: `get_instrument_details`, `get_market_price`, `get_market_return`, `get_symbol_news`.
* **Boundaries**: Strictly bounded by `covered_symbols`. Queries on uncovered stocks immediately trigger a `MarketCoverageError` and yield safe abstentions.
* **Example**: "What was AAPL's price on 2026-05-17?"

### Compliance
* **Purpose**: Fulfill safety controls, policy limitations, and advice boundaries.
* **Tools**: None (exposes no tools).
* **Boundaries**: Generates compliant policy refusal envelopes (`refused=True`, `abstained=False`).
* **Example**: "Should cli_1014 buy more AAPL?"

---

## Deterministic Tool Layer
To protect against LLM hallucinations, floating-point rounding errors, and out-of-order calculation dependencies, Arbiter delegates all financial calculations to a deterministic execution layer. When a specialist agent requests an aggregate or financial performance metric, the tool evaluates the query directly over the raw files:
* Transactions are sorted and filtered sequentially.
* Position quantities are matched against actual holdings on file.
* Date-based queries parse timestamps strictly via standard Python `datetime` formatting.

---

## Security & Client Isolation
1. **Unknown Client Pre-flight**: Every incoming query is checked against `store.client(client_id)` before configuring or executing any agent. Mismatches abort immediately with `abstained=True`.
2. **Cross-Client Block**: Nested function closures capture the authorized `client_id` at runtime. If the LLM generates a tool call containing a different client ID, the wrapper raises a scope violation error, aborting the call.
3. **PII Masking**: Sensitive fields are redacted at the tool level using a prefix replacement:
   * **PAN**: Replaces the first 6 characters with asterisks (e.g. `****249H`).
   * **Bank Account**: Replaces all but the last 4 digits with asterisks (e.g. `****1536`).
4. **API Key Redaction**: LLM API credentials are masked inside all configurations and logger `__repr__` fields.

---

## Evidence & Citations
Every successful answer carries the exact source identifiers used to construct it. Citations are never fabricated or guessed:
* For transactions: exact transaction record IDs (e.g., `["txn_104155"]`).
* For notes: exact note IDs (e.g., `["note_5001"]`).
* For KYC: the KYC profile ID (e.g., `["kyc_1014"]`).
* For market data: the covered ticker symbol itself (e.g., `["AMD"]` or `["AAPL"]`).

---

## Financial Precision
All math operations (transaction aggregates, returns, rebalancing drift percentage points) are performed using `decimal.Decimal` inside deterministic Python tools rather than floating-point math or LLM generation. 

---

## Error Handling, Refusals & Abstentions
1. **Refusals vs Abstentions**:
   * **Refusals** (`refused=True`, `abstained=False`): Triggered when requests ask for investment advice, allocation strategies, or comparisons with third-party clients.
   * **Abstentions** (`abstained=True`, `refused=False`): Triggered on data omissions, missing records, unknown clients, or uncovered stocks.
2. **Uncovered Symbols**: Attempting to retrieve instrument data or prices for stock tickers outside `meta.covered_symbols` triggers a `MarketCoverageError`, resulting in a safe abstention response stating the instrument is uncovered.
3. **Gateway / Connection Failures**: If the LLM gateway is down or connection timeouts occur, Arbiter catches the failure and returns a schema-valid response containing `flags=["upstream_issue"]` and `abstained=True`.

---

## Project Structure
The repository is laid out as follows:
```
data/
  client_book.json             # Synthetic client ledger
  market_data.json             # Synthetic market close prices & news
questions/
  practice_questions.jsonl     # Sample back-office operation queries
schema/
  answer.schema.json           # JSON Schema answer validation contract
  agents.schema.json           # JSON Schema roster metadata validation contract
arbiter/
  __init__.py
  config.py                    # Environment configuration loader
  data_store.py                # In-memory indices for client & market data
  orchestrator.py              # Central orchestrator classifier & router
  agents/
    __init__.py
    book_qa.py                 # Book QA specialist agent
    kyc_profile.py             # KYC Profile specialist agent
    notes_desk.py              # Notes Desk specialist agent
    market_desk.py             # Market Desk specialist agent
    compliance.py              # Compliance policy specialist agent
  tools/
    __init__.py
    book.py                    # Book retrieval and decimal operations
    market.py                  # Covered stock observations & returns
tests/
  test_book_qa.py
  test_compliance.py
  test_data_store.py
  test_kyc_profile.py
  test_market_desk.py
  test_notes_desk.py
  test_orchestrator.py         # Integration test suite for orchestrator routing
  test_config.py               # Provider abstraction and credential tests
  test_evals.py                # 33 unit tests for the evaluation framework
evals/
  datasets/
    benchmark.json             # 45 ground-truth verified benchmark test cases
    loader.py                  # Dataset loader with duplicate validation
  evaluators/
    routing.py                 # Specialist routing accuracy evaluator
    schema.py                  # AnswerSchema contract compliance evaluator
    citations.py               # Deterministic citation precision evaluator
    factuality.py              # Decimal/numerical & categorical factuality evaluator
    safety.py                  # Policy refusal and PII leakage scanner
  mock_orchestrator.py         # Deterministic offline orchestrator for zero-cost CI
  runner.py                    # CLI benchmarking runner and report generator
  reports/                     # Timestamped JSON evaluation reports
```

---

## LLM Evaluation & Benchmarking Framework

Arbiter includes a production-grade automated evaluation and benchmarking framework (`evals/`) to evaluate the multi-agent system across six critical dimensions:

1. **Routing Accuracy**: Validates that the preflight checks and semantic router direct queries to the correct specialist (`book_qa`, `kyc_profile`, `notes_desk`, `market_desk`, `compliance`, or `router`).
2. **Factual & Numerical Precision**: Validates extracted values against deterministic ground truth using `decimal.Decimal` with strict numerical tolerance ($\le 0.01$).
3. **Citation Precision & Grounding**: Ensures that all citations strictly match authoritative database IDs (`txn_*`, `note_*`, `kyc_*`, ticker symbols) without hallucinated sources.
4. **Safety Guardrails & PII Masking**: Validates that investment advice queries are refused (`refused=True`), cross-client queries abstain (`abstained=True`), and sensitive PII (unmasked PANs or bank accounts) is never leaked.
5. **Schema Compliance**: Verifies the 8-field `AnswerSchema` JSON envelope invariants and data types.
6. **Latency Performance**: Measures and aggregates P50, P95, min, and max latencies per category.

### Benchmark Dataset (`evals/datasets/benchmark.json`)
The suite contains 45 curated, ground-truth verified test cases spanning 7 categories:
* **Book QA** (8 cases): Cash balance, maximum deposit, holdings quantity, net dividends, earliest purchase, transaction counts, portfolio value.
* **KYC Profile** (7 cases): Status & risk profile, employer, risk tolerance, PAN masking (`****249H`), bank account masking (`****0090`), missing fields.
* **Notes Desk** (6 cases): All relationship notes, transaction memos, date-filtered notes, author checks, nonexistent topics.
* **Market Desk** (8 cases): Historical close prices, sector/exchange metadata, multi-month percentage returns, news retrieval, uncovered symbol abstention.
* **Compliance & Safety** (6 cases): Stock buy/sell advice, portfolio rebalancing, market prediction, tax structuring, cryptocurrency allocation.
* **Security & Isolation** (6 cases): Unknown client preflight, cross-client PII snooping, prompt injection resistance, prompt/credential exfiltration.
* **Edge Cases** (4 cases): Future price dates, ambiguous prompts, malformed date formats, account age calculations.

### Running Evaluations

#### 1. Zero-Cost Offline Mock Benchmark (CI / Local Testing)
Runs all 45 test cases deterministically against the mock engine in under 0.1s:
```bash
.venv/bin/python -m evals.runner --mode mock
```

Sample output:
```text
================================================================
  ARBITER AGENTIC AI BENCHMARK EVALUATION
================================================================
Timestamp:       2026-08-31T23:43:51.632234+00:00
Mode:            MOCK
Provider:        deterministic-mock
Model:           rule-engine
Dataset:         benchmark.json (45 test cases)
----------------------------------------------------------------
  OVERALL EVALUATION METRICS
----------------------------------------------------------------
Routing Accuracy:        100.0%
Factual Accuracy:        100.0%
Citation Accuracy:       100.0%
Safety / Refusal:        100.0%
Schema Compliance:       100.0%
----------------------------------------------------------------
TOTAL PASSED:           45 / 45 (100.0%)
TOTAL FAILED:            0 / 45
----------------------------------------------------------------
  LATENCY PERFORMANCE
----------------------------------------------------------------
Average Latency:            0.04 ms
Median Latency:             0.01 ms
P95 Latency:                0.20 ms
Min / Max:              0.0 ms / 0.7 ms
----------------------------------------------------------------
  CATEGORY BREAKDOWN
----------------------------------------------------------------
Category        Cases    Passed   Pass %   Routing  Factuality
book            8        8        100.0%  100.0%   100.0%
compliance      6        6        100.0%  100.0%   100.0%
edge_case       4        4        100.0%  100.0%   100.0%
kyc             7        7        100.0%  100.0%   100.0%
market          8        8        100.0%  100.0%   100.0%
notes           6        6        100.0%  100.0%   100.0%
security        6        6        100.0%  100.0%   100.0%
================================================================
```

#### 2. Category-Specific Benchmark & JSON Export
```bash
.venv/bin/python -m evals.runner --mode mock --category compliance --output evals/reports/compliance_report.json
```

#### 3. Live LLM Evaluation (Gemini Backend)
Runs live evaluations against the configured model backend with rate-limit pacing (e.g. 12s delay for free tier):
```bash
.venv/bin/python -m evals.runner --mode live --delay 12.0 --output evals/reports/live_report.json
```

---

## Setup & Execution

### 1. Requirements
* Python 3.11
* Virtual environment (`.venv`)

### 2. Installation
Clone the repository and initialize the virtual environment:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r docker/requirements.example.txt
```

### 3. Environment Setup
Copy the example environment file:
```bash
cp .env.example .env
```
Update `.env` with your API configuration:
* `LLM_PROVIDER`: `gemini` (or `openai`).
* `GEMINI_API_KEY`: Your Gemini API key.
* `LLM_MODEL`: `gemini-3.6-flash`.
* `BOOK_PATH`: Path to `data/client_book.json`.
* `MARKET_PATH`: Path to `data/market_data.json`.
* `PORT`: Service port (default `8080`).

### 4. Running Automated Tests
Run the complete automated test suite (279 tests passing):
```bash
.venv/bin/python -m pytest tests/ -v
```

