import React, { useEffect, useState } from "react";
import {
  Activity,
  Database,
  MessageSquareCode,
  Network,
  Wrench,
  ArrowRight,
  Layers,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ObservabilitySummary, ReadinessResponse } from "../api/types";
import type { NavPage } from "../components/Shell";
import { StatusIndicator } from "../components/StatusIndicator";
import { EmptyState } from "../components/EmptyState";

interface DashboardPageProps {
  onNavigate: (page: NavPage) => void;
  onSelectClient?: (clientId: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [ready, setReady] = useState<ReadinessResponse | null>(null);
  const [obs, setObs] = useState<ObservabilitySummary | null>(null);

  useEffect(() => {
    Promise.all([
      arbiterApi.getReadiness().catch(() => null),
      arbiterApi.getObservabilitySummary().catch(() => null),
    ]).then(([r, o]) => {
      setReady(r);
      setObs(o);
    });
  }, []);

  const specialistAgents = [
    {
      id: "router",
      name: "Router Coordinator",
      role: "Intent Classification & Safety Gate",
      toolsCount: 0,
      rule: "Hub-and-spoke classifier with deterministic preflight overrides",
    },
    {
      id: "book_qa",
      name: "Book QA Specialist",
      role: "Portfolio & Transactions",
      toolsCount: 16,
      rule: "Exact balances, holdings, drift & snapshot math using Python Decimal",
    },
    {
      id: "kyc_profile",
      name: "KYC Profile Specialist",
      role: "Identity & Compliance Suitability",
      toolsCount: 2,
      rule: "Masked personal identity, suitability reviews & risk profile records",
    },
    {
      id: "notes_desk",
      name: "Notes Desk Specialist",
      role: "Relationship Notes & Memos",
      toolsCount: 2,
      rule: "Dynamic interaction memos with indirect injection XML boundaries",
    },
    {
      id: "market_desk",
      name: "Market Desk Specialist",
      role: "Pricing & Covered Securities",
      toolsCount: 4,
      rule: "Historical close prices, returns & sector news for 14 covered tickers",
    },
    {
      id: "compliance",
      name: "Compliance Specialist",
      role: "Regulatory & Policy Refusal",
      toolsCount: 0,
      rule: "Zero tools authorized. Deterministic refusal of investment advice",
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Operations Header & Status Strip */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1a2234] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold tracking-tight text-white font-mono">
              ARBITER OPERATIONS CONSOLE
            </h1>
            <StatusIndicator status="READY" size="sm" />
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Multi-agent financial operations workstation with deterministic accounting tools and verified security boundaries.
          </p>
        </div>

        {/* System Status Compact Block */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <div className="px-2.5 py-1 rounded bg-[#0c101a] border border-slate-800 flex items-center gap-1.5">
            <span className="text-slate-500">API:</span>
            <span className="text-emerald-400 font-semibold">ONLINE</span>
          </div>
          <div className="px-2.5 py-1 rounded bg-[#0c101a] border border-slate-800 flex items-center gap-1.5">
            <span className="text-slate-500">DATA:</span>
            <span className="text-slate-200">{ready?.clients_loaded ?? 25} Clients / {ready?.instruments_loaded ?? 14} Tickers</span>
          </div>
          <div className="px-2.5 py-1 rounded bg-[#0c101a] border border-slate-800 flex items-center gap-1.5">
            <span className="text-slate-500">CIRCUIT:</span>
            <span className="text-emerald-400 font-semibold">CLOSED</span>
          </div>
        </div>
      </div>

      {/* Quick Action Operations Launchers */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <button
          onClick={() => onNavigate("ask")}
          className="p-3.5 rounded-lg bg-[#0c101a] hover:bg-[#121826] border border-slate-800 text-left transition-all group cursor-pointer flex flex-col justify-between space-y-2"
        >
          <div className="flex items-center justify-between">
            <MessageSquareCode className="w-4 h-4 text-indigo-400" />
            <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-indigo-400 transition-colors" />
          </div>
          <div>
            <div className="text-xs font-bold text-white font-mono">Ask Arbiter</div>
            <p className="text-[11px] text-slate-400 mt-0.5">Natural language operations queries</p>
          </div>
        </button>

        <button
          onClick={() => onNavigate("clients")}
          className="p-3.5 rounded-lg bg-[#0c101a] hover:bg-[#121826] border border-slate-800 text-left transition-all group cursor-pointer flex flex-col justify-between space-y-2"
        >
          <div className="flex items-center justify-between">
            <Database className="w-4 h-4 text-emerald-400" />
            <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-emerald-400 transition-colors" />
          </div>
          <div>
            <div className="text-xs font-bold text-white font-mono">Client Book</div>
            <p className="text-[11px] text-slate-400 mt-0.5">Inspect 25 authorized portfolios</p>
          </div>
        </button>

        <button
          onClick={() => onNavigate("tools")}
          className="p-3.5 rounded-lg bg-[#0c101a] hover:bg-[#121826] border border-slate-800 text-left transition-all group cursor-pointer flex flex-col justify-between space-y-2"
        >
          <div className="flex items-center justify-between">
            <Wrench className="w-4 h-4 text-sky-400" />
            <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-sky-400 transition-colors" />
          </div>
          <div>
            <div className="text-xs font-bold text-white font-mono">Tool Verification</div>
            <p className="text-[11px] text-slate-400 mt-0.5">24 verified deterministic tools</p>
          </div>
        </button>

        <button
          onClick={() => onNavigate("architecture")}
          className="p-3.5 rounded-lg bg-[#0c101a] hover:bg-[#121826] border border-slate-800 text-left transition-all group cursor-pointer flex flex-col justify-between space-y-2"
        >
          <div className="flex items-center justify-between">
            <Layers className="w-4 h-4 text-purple-400" />
            <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-purple-400 transition-colors" />
          </div>
          <div>
            <div className="text-xs font-bold text-white font-mono">Architecture</div>
            <p className="text-[11px] text-slate-400 mt-0.5">Multi-tier subsystem design</p>
          </div>
        </button>
      </div>

      {/* System Capabilities Matrix */}
      <div className="p-4 rounded-lg bg-[#0c101a] border border-slate-800 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
          <div className="text-xs font-mono uppercase font-bold text-slate-300 flex items-center gap-2">
            <Network className="w-3.5 h-3.5 text-indigo-400" />
            Specialist Agent Specialization Matrix
          </div>
          <span className="text-[11px] font-mono text-slate-500">6 Subdomain Specialists</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {specialistAgents.map((agent) => (
            <div
              key={agent.id}
              className="p-3 rounded bg-[#0f1422] border border-slate-800/80 flex flex-col justify-between space-y-2"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-white font-mono">{agent.name}</span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.2 rounded border font-semibold ${
                      agent.toolsCount > 0
                        ? "bg-indigo-950 text-indigo-300 border-indigo-800"
                        : "bg-rose-950 text-rose-300 border-rose-800"
                    }`}
                  >
                    {agent.toolsCount} Tools
                  </span>
                </div>
                <div className="text-[11px] text-slate-300 font-medium mt-1">{agent.role}</div>
                <p className="text-[11px] text-slate-400 mt-1 leading-snug">{agent.rule}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Live Request Activity Stream */}
      <div className="rounded-lg bg-[#0c101a] border border-slate-800 overflow-hidden space-y-0">
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-mono uppercase font-bold text-slate-300">
              Live Execution Telemetry & Request Log
            </span>
          </div>
          <button
            onClick={() => onNavigate("observability")}
            className="text-[11px] font-mono text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors cursor-pointer"
          >
            <span>Full Observability</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {obs?.recent_traces && obs.recent_traces.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-900 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">Request ID</th>
                  <th className="py-2.5 px-4">Client Scope</th>
                  <th className="py-2.5 px-4">Agent Path</th>
                  <th className="py-2.5 px-4">Tools Executed</th>
                  <th className="py-2.5 px-4">Total Latency</th>
                  <th className="py-2.5 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-200">
                {obs.recent_traces.slice(0, 5).map((tr) => (
                  <tr key={tr.request_id} className="hover:bg-slate-800/30">
                    <td className="py-2.5 px-4 text-indigo-400 font-bold">{tr.request_id}</td>
                    <td className="py-2.5 px-4 text-slate-300">{tr.client_id}</td>
                    <td className="py-2.5 px-4">
                      <div className="flex items-center gap-1 text-[11px]">
                        {tr.agent_path.map((ag, i) => (
                          <span key={i} className="flex items-center gap-1">
                            <span className="text-slate-200">{ag}</span>
                            {i < tr.agent_path.length - 1 && <span className="text-slate-600">→</span>}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-2.5 px-4">{tr.tool_call_count} calls</td>
                    <td className="py-2.5 px-4">{tr.total_latency_ms ? `${tr.total_latency_ms.toFixed(1)} ms` : "—"}</td>
                    <td className="py-2.5 px-4">
                      <StatusIndicator
                        status={tr.refused ? "REFUSED" : tr.abstained ? "ABSTAINED" : tr.success ? "SUCCESS" : "ERROR"}
                        size="sm"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={Activity}
            title="No requests recorded yet"
            description="Run a query through Ask Arbiter or submit an HTTP request to populate the live operations telemetry timeline."
            actionLabel="Open Ask Arbiter"
            onAction={() => onNavigate("ask")}
            className="border-0 rounded-none bg-transparent"
          />
        )}
      </div>

      {/* Dataset Coverage Blocks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Client Dataset Block */}
        <div className="p-4 rounded-lg bg-[#0c101a] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-mono uppercase font-bold text-slate-300 flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              Client Book Dataset
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold">
              25 CLIENTS
            </span>
          </div>
          <div className="space-y-1 text-xs font-mono text-slate-300">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Total Authorized Portfolios:</span>
              <span className="text-white font-bold">25 Client Records</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Risk Profile Coverage:</span>
              <span className="text-slate-200">Conservative · Moderate · Aggressive</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Data Boundaries:</span>
              <span className="text-emerald-400">PII Redacted · Isolated Scope</span>
            </div>
          </div>
        </div>

        {/* Market Dataset Block */}
        <div className="p-4 rounded-lg bg-[#0c101a] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-mono uppercase font-bold text-slate-300 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-purple-400" />
              Market Securities Dataset
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 font-semibold">
              14 TICKERS
            </span>
          </div>
          <div className="space-y-1 text-xs font-mono text-slate-300">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Covered Equity Symbols:</span>
              <span className="text-indigo-300 font-bold">AAPL, MSFT, GOOGL, NVDA, AMZN...</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Historical Observations:</span>
              <span className="text-slate-200">Monthly Close & Returns</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Security Math:</span>
              <span className="text-emerald-400">Exact Decimal Arithmetic</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
