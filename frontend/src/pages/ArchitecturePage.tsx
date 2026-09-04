import React from "react";
import {
  Layers,
  ArrowDown,
  Cpu,
  ShieldCheck,
  Wrench,
  Activity,
  BarChart3,
  Server,
  Lock,
  Workflow,
  CheckCircle2,
} from "lucide-react";

export const ArchitecturePage: React.FC = () => {
  const executionStages = [
    {
      num: "01",
      title: "Client & Operations Console",
      tech: "React 19 · TypeScript · Vite · Tailwind CSS",
      icon: Cpu,
      color: "border-indigo-800/80 bg-indigo-950/20 text-indigo-300",
      description:
        "Operations workstation rendering authoritative backend metadata. Never computes financial values client-side; strictly submits typed queries with context-bound client identifiers.",
    },
    {
      num: "02",
      title: "FastAPI Service Boundary",
      tech: "FastAPI · Pydantic v2 · Uvicorn · ASGIMiddleware",
      icon: Server,
      color: "border-sky-800/80 bg-sky-950/20 text-sky-300",
      description:
        "Asynchronous transport layer enforcing QueryRequest schemas, correlation X-Request-ID propagation, security response headers, and threadpool delegation for blocking operations.",
    },
    {
      num: "03",
      title: "Ingress Security Boundary",
      tech: "InputGuard · Regex Pattern Scanner",
      icon: Lock,
      color: "border-rose-800/80 bg-rose-950/20 text-rose-300",
      description:
        "Pre-flight injection defense detecting jailbreaks, system prompt extraction, and role hijacking before invoking downstream models. Validates client authorization.",
    },
    {
      num: "04",
      title: "Arbiter Orchestrator",
      tech: "ArbiterOrchestrator · Hub-and-Spoke Coordinator",
      icon: Workflow,
      color: "border-purple-800/80 bg-purple-950/20 text-purple-300",
      description:
        "Central coordinator orchestrating intent routing, specialist dispatch, execution budgets, and synthesized AnswerSchema responses.",
    },
    {
      num: "05",
      title: "Router & Specialist Agents",
      tech: "6 Domain Agents (Router, Book QA, KYC, Notes, Market, Compliance)",
      icon: Layers,
      color: "border-amber-800/80 bg-amber-950/20 text-amber-300",
      description:
        "Specialist agents dedicated to specific financial subdomains. The Compliance agent possesses zero tools to enforce deterministic policy refusals.",
    },
    {
      num: "06",
      title: "Tool Verification Layer",
      tech: "TOOL_REGISTRY · ToolVerifier · Scope Guard",
      icon: Wrench,
      color: "border-emerald-800/80 bg-emerald-950/20 text-emerald-300",
      description:
        "Strict authorization checkpoint validating agent permissions, client scope isolation, and Pydantic argument schemas before invoking deterministic tools.",
    },
    {
      num: "07",
      title: "Deterministic Financial Tools",
      tech: "24 Tools · Python decimal.Decimal · In-Memory DataStore",
      icon: CheckCircle2,
      color: "border-teal-800/80 bg-teal-950/20 text-teal-300",
      description:
        "Zero LLM arithmetic. 100% deterministic accounting, transaction querying, KYC retrieval, memo filtering, and price lookup over immutable JSON datasets.",
    },
    {
      num: "08",
      title: "Output Sanitization & Schema Validation",
      tech: "AnswerSchema Contract · PII Masker · Secret Redactor",
      icon: ShieldCheck,
      color: "border-indigo-800/80 bg-indigo-950/20 text-indigo-300",
      description:
        "Final guardrail masking Indian PANs (****249H) and bank accounts (****9012), validating record citations, and ensuring typed responses.",
    },
  ];

  const crossCuttingSystems = [
    {
      title: "Security & Trust",
      icon: ShieldCheck,
      color: "border-rose-800/80 bg-rose-950/20 text-rose-300",
      items: [
        "Pre-flight regex jailbreak defense",
        "XML quarantine (<untrusted_retrieved_data>)",
        "Runtime client isolation closures",
        "Automated PAN and bank account PII masking",
        "API key and secret leak scrubbers",
      ],
    },
    {
      title: "Reliability & Fault Tolerance",
      icon: Activity,
      color: "border-amber-800/80 bg-amber-950/20 text-amber-300",
      items: [
        "Circuit breaker (5 failures / 30s recovery)",
        "Exponential backoff with full equal jitter (1-8s)",
        "15.0s per-invocation execution budget",
        "Non-retryable client error fast-fail",
        "Deterministic abstention fallback envelope",
      ],
    },
    {
      title: "Observability & Audit",
      icon: BarChart3,
      color: "border-sky-800/80 bg-sky-950/20 text-sky-300",
      items: [
        "End-to-end RequestTrace collector",
        "P50 and P95 latency percentile tracking",
        "Agent path and tool execution counting",
        "Structured sanitized JSONL logging",
        "Unique correlation X-Request-ID propagation",
      ],
    },
  ];

  const agentToolMatrix = [
    {
      agent: "Book QA",
      toolsCount: 16,
      domain: "Portfolio, Accounts, Holdings & Transactions",
      scope: "Strictly Client-Scoped",
      tools:
        "get_client_profile, get_client_accounts, get_client_holdings, get_account_holdings, calculate_portfolio_value, calculate_cash_balance, get_historical_transactions, filter_transactions_by_date, filter_transactions_by_type, calculate_total_transacted_amount, get_earliest_transaction, get_latest_transaction, calculate_realized_gain_loss, get_asset_allocation, get_portfolio_drift, get_account_snapshot",
    },
    {
      agent: "Market Desk",
      toolsCount: 4,
      domain: "Pricing, Observations, Returns & Securities News",
      scope: "Global Market Scope",
      tools:
        "get_security_price_on_date, get_latest_market_observation, calculate_security_return, get_market_news",
    },
    {
      agent: "KYC Profile",
      toolsCount: 2,
      domain: "Identity, Employment, Suitability & Risk Profile",
      scope: "Strictly Client-Scoped",
      tools: "get_kyc_details, get_suitability_assessment",
    },
    {
      agent: "Notes Desk",
      toolsCount: 2,
      domain: "CRM Interaction History & Advisor Memos",
      scope: "Strictly Client-Scoped",
      tools: "get_advisor_notes, search_client_memos",
    },
    {
      agent: "Compliance",
      toolsCount: 0,
      domain: "Deterministic Policy Refusal & Scope Guard",
      scope: "Refusal Authority",
      tools: "No tools authorized (Deterministic policy refusal)",
    },
    {
      agent: "Router Coordinator",
      toolsCount: 0,
      domain: "Intent Classification & Safety Override",
      scope: "Pipeline Ingress",
      tools: "No tools authorized (Delegation authority only)",
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="border-b border-[#1a2234] pb-4">
        <div className="flex items-center gap-2.5">
          <h1 className="text-lg font-bold tracking-tight text-white font-mono flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            SYSTEM ARCHITECTURE & SUBSYSTEM BOUNDARIES
          </h1>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/40 text-indigo-300 border border-indigo-800/60 font-semibold">
            MULTI-TIER PLATFORM
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">
          End-to-end multi-tier execution lifecycle, domain specialization, deterministic tool authorization, and cross-cutting controls.
        </p>
      </div>

      {/* Execution Pipeline */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
            Execution Lifecycle (Ingress → Orchestration → Deterministic Tools → Output)
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            8-Tier Sequence
          </span>
        </div>

        <div className="space-y-2">
          {executionStages.map((stage, idx) => {
            const Icon = stage.icon;
            return (
              <React.Fragment key={idx}>
                <div
                  className={`p-3.5 rounded-lg border flex flex-col md:flex-row md:items-center justify-between gap-3 ${stage.color}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="p-1.5 rounded bg-slate-900 border border-slate-700/80 text-white shrink-0 mt-0.5">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-mono font-bold text-slate-400">
                          STAGE {stage.num}
                        </span>
                        <h3 className="text-xs font-bold text-white font-mono">
                          {stage.title}
                        </h3>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900/80 border border-slate-700/60 text-slate-300">
                          {stage.tech}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mt-1 leading-relaxed font-sans">
                        {stage.description}
                      </p>
                    </div>
                  </div>
                </div>

                {idx < executionStages.length - 1 && (
                  <div className="flex justify-center my-0.5 text-slate-600">
                    <ArrowDown className="w-3.5 h-3.5" />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Cross-Cutting Systems */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
            Cross-Cutting Subsystem Controls
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Platform Guarantees
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {crossCuttingSystems.map((sys, idx) => {
            const Icon = sys.icon;
            return (
              <div
                key={idx}
                className={`p-3.5 rounded-lg border flex flex-col justify-between space-y-2.5 ${sys.color}`}
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2 pb-2 border-b border-slate-800/60">
                    <Icon className="w-4 h-4" />
                    <span className="font-bold text-xs text-white font-mono uppercase">
                      {sys.title}
                    </span>
                  </div>
                  <ul className="space-y-1 text-xs text-slate-300 font-mono">
                    {sys.items.map((item, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-slate-500 font-bold">▸</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Agent to Tool Authorization Matrix */}
      <div className="rounded-lg bg-[#0c101a] border border-slate-800 overflow-hidden shadow-sm space-y-0 pt-1">
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="text-xs font-mono uppercase font-bold text-slate-300">
            Agent → Authorized Tool Registry Matrix (24 Tools Total)
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Explicit Authoritative Bounds
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-4">Agent Specialist</th>
                <th className="py-2.5 px-4">Tools Count</th>
                <th className="py-2.5 px-4">Domain Scope</th>
                <th className="py-2.5 px-4">Authorized Tool List</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {agentToolMatrix.map((item, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4 text-white font-bold">
                    {item.agent}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        item.toolsCount > 0
                          ? "bg-indigo-950 text-indigo-300 border-indigo-800"
                          : "bg-rose-950 text-rose-300 border-rose-800"
                      }`}
                    >
                      {item.toolsCount} tools
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    <div>{item.domain}</div>
                    <div className="text-[10px] text-slate-500">{item.scope}</div>
                  </td>
                  <td className="py-3 px-4 text-[11px] text-slate-400 max-w-md leading-relaxed">
                    {item.tools}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
