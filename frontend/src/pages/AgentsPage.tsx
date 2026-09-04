import React, { useEffect, useState } from "react";
import {
  Network,
  RefreshCw,
  Layers,
  ArrowRight,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import { StatusIndicator } from "../components/StatusIndicator";

export const AgentsPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);

  const loadAgents = () => {
    setLoading(true);
    arbiterApi
      .getAgents()
      .then(() => {
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const specialistHierarchy = [
    {
      id: "router",
      name: "Router Coordinator",
      role: "Hub Classification & Policy Gate",
      toolCount: 0,
      scope: "Preflight Ingress",
      boundary: "Deterministic keyword overrides for investment advice & compliance",
      description:
        "Evaluates incoming natural language requests, applies deterministic preflight safety overrides, and delegates to domain specialists.",
      isHub: true,
    },
    {
      id: "book_qa",
      name: "Book QA Specialist",
      role: "Portfolio, Accounts & Transactions",
      toolCount: 16,
      scope: "Client-Scoped",
      boundary: "Strict client_id context isolation; Decimal arithmetic engine",
      description:
        "Executes 16 deterministic financial tools to calculate portfolio balances, transaction totals, asset allocation, holdings drift, and account snapshots.",
      isHub: false,
    },
    {
      id: "kyc_profile",
      name: "KYC Profile Specialist",
      role: "Identity & Suitability Compliance",
      toolCount: 2,
      scope: "Client-Scoped",
      boundary: "Automated Indian PAN (****249H) and bank account (****9012) masking",
      description:
        "Retrieves masked identity records, employment details, income brackets, suitability reviews, and risk profile ratings.",
      isHub: false,
    },
    {
      id: "notes_desk",
      name: "Notes Desk Specialist",
      role: "CRM & Relationship Intelligence",
      toolCount: 2,
      scope: "Client-Scoped",
      boundary: "Strict XML boundary encapsulation (<untrusted_retrieved_data>)",
      description:
        "Searches relationship notes, author history, and transaction memos with indirect prompt injection quarantine safeguards.",
      isHub: false,
    },
    {
      id: "market_desk",
      name: "Market Desk Specialist",
      role: "Pricing & Covered Securities",
      toolCount: 4,
      scope: "Global Market Scope",
      boundary: "Restricted strictly to 14 covered equity tickers",
      description:
        "Answers factual equity pricing queries, monthly close observations, historical returns, and covered securities news.",
      isHub: false,
    },
    {
      id: "compliance",
      name: "Compliance Specialist",
      role: "Regulatory & Policy Refusal",
      toolCount: 0,
      scope: "Refusal Authority",
      boundary: "Zero tools authorized. Deterministic policy refusal",
      description:
        "Safety refusal agent handling out-of-scope requests, cross-client queries, and personalized investment/allocation advice.",
      isHub: false,
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1a2234] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold tracking-tight text-white font-mono flex items-center gap-2">
              <Network className="w-4 h-4 text-indigo-400" />
              SPECIALIST AGENT NETWORK
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/40 text-indigo-300 border border-indigo-800/60 font-semibold">
              6 SPECIALIST ROLES
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Hub-and-spoke multi-agent topology separating ingress classification, domain specialization, and policy refusal.
          </p>
        </div>

        <button
          onClick={loadAgents}
          disabled={loading}
          className="self-start md:self-auto px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-xs font-mono text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin text-indigo-400" : ""}`} />
          <span>Refresh Agents</span>
        </button>
      </div>

      {/* Hub: Router Coordinator */}
      <div className="p-4 rounded-lg bg-[#0c101a] border border-indigo-700/60 shadow-md space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-indigo-950 border border-indigo-700/80 text-indigo-300">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-white font-mono">
                  {specialistHierarchy[0].name}
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                  COORDINATION HUB
                </span>
              </div>
              <div className="text-xs text-slate-300">{specialistHierarchy[0].role}</div>
            </div>
          </div>
          <StatusIndicator status="CONFIGURED" size="sm" />
        </div>
        <p className="text-xs text-slate-300 leading-relaxed font-sans">
          {specialistHierarchy[0].description}
        </p>
        <div className="pt-1 flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400 border-t border-slate-800/80">
          <span>Security: <strong className="text-emerald-400">{specialistHierarchy[0].boundary}</strong></span>
        </div>
      </div>

      {/* Spokes: 5 Domain Specialist Agents */}
      <div className="space-y-3">
        <div className="text-xs font-mono uppercase font-bold text-slate-400 flex items-center gap-1.5">
          <ArrowRight className="w-3.5 h-3.5 text-indigo-400" />
          Domain Specialist Spokes (Delegated Execution)
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {specialistHierarchy.slice(1).map((agent) => (
            <div
              key={agent.id}
              className="p-4 rounded-lg bg-[#0c101a] border border-slate-800 flex flex-col justify-between space-y-3"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-xs text-white font-mono">
                      {agent.name}
                    </h3>
                    <div className="text-[11px] text-slate-400 font-medium">
                      {agent.role}
                    </div>
                  </div>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.2 rounded border font-semibold ${
                      agent.toolCount > 0
                        ? "bg-indigo-950 text-indigo-300 border-indigo-800"
                        : "bg-rose-950 text-rose-300 border-rose-800"
                    }`}
                  >
                    {agent.toolCount} Tools
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed font-sans">
                  {agent.description}
                </p>
              </div>

              <div className="pt-2 border-t border-slate-800/80 space-y-1 text-[10px] font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Scope:</span>
                  <span className="text-slate-200">{agent.scope}</span>
                </div>
                <div className="text-slate-400 truncate">
                  Boundary: <span className="text-emerald-400">{agent.boundary}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
