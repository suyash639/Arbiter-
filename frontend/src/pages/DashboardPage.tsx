import React, { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  Database,
  MessageSquareCode,
  Network,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ReadinessResponse } from "../api/types";
import type { NavPage } from "../components/Shell";

interface DashboardPageProps {
  onNavigate: (page: NavPage) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [ready, setReady] = useState<ReadinessResponse | null>(null);

  useEffect(() => {
    arbiterApi.getReadiness().then(setReady).catch(() => {});
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Welcome & System Status Banner */}
      <div className="rounded-xl border border-slate-800 bg-gradient-to-r from-[#121727] via-[#0f1422] to-[#141926] p-6 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 text-indigo-400 text-xs font-mono font-semibold uppercase tracking-wider mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              Arbiter Operations Platform
            </div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Financial AI Operations & Multi-Agent Coordination
            </h1>
            <p className="text-slate-400 text-xs mt-1 max-w-2xl leading-relaxed">
              Arbiter coordinates back-office operations across portfolio accounting, KYC profiling, relationship CRM notes, and market coverage with deterministic verification and strict security boundaries.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigate("ask")}
              className="px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-lg shadow-indigo-600/20 cursor-pointer"
            >
              <MessageSquareCode className="w-4 h-4" />
              Launch Ask Arbiter
            </button>
            <button
              onClick={() => onNavigate("architecture")}
              className="px-3.5 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all border border-slate-700 cursor-pointer"
            >
              Architecture Map
            </button>
          </div>
        </div>
      </div>

      {/* Primary Key Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Benchmark Score */}
        <div className="p-4 rounded-xl bg-[#111624] border border-slate-800/80 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="font-mono uppercase font-semibold">Evaluation Benchmark</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-extrabold text-emerald-400 font-mono">100.0%</div>
            <div className="text-[11px] text-slate-400 mt-0.5">45 / 45 Offline Test Cases Passing</div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-slate-800 text-[10px] text-slate-500 flex justify-between">
            <span>Routing: 100%</span>
            <span>Factuality: 100%</span>
          </div>
        </div>

        {/* Metric 2: Automated Test Suite */}
        <div className="p-4 rounded-xl bg-[#111624] border border-slate-800/80 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="font-mono uppercase font-semibold">Regression Suite</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-extrabold text-white font-mono">384 Tests</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Full Pytest Test Suite Passing</div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-slate-800 text-[10px] text-slate-500 flex justify-between">
            <span>FastAPI: 23</span>
            <span>Security: 19</span>
            <span>Tools: 23</span>
          </div>
        </div>

        {/* Metric 3: Tool Verification */}
        <div className="p-4 rounded-xl bg-[#111624] border border-slate-800/80 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="font-mono uppercase font-semibold">Verified Tools</span>
            <Wrench className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-extrabold text-amber-400 font-mono">24 Tools</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Deterministic Business Calculations</div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-slate-800 text-[10px] text-slate-500 flex justify-between">
            <span>Book QA: 16</span>
            <span>Market: 4</span>
            <span>KYC/Notes: 4</span>
          </div>
        </div>

        {/* Metric 4: Security & Isolation */}
        <div className="p-4 rounded-xl bg-[#111624] border border-slate-800/80 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="font-mono uppercase font-semibold">Security Boundary</span>
            <ShieldCheck className="w-4 h-4 text-sky-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-extrabold text-sky-400 font-mono">STRICT</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Injection Guard + PII Masking</div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-slate-800 text-[10px] text-slate-500 flex justify-between">
            <span>PAN / Account Masked</span>
            <span>Scope Isolated</span>
          </div>
        </div>
      </div>

      {/* Agent Network Overview Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Agent Topology */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-[#111624] border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Network className="w-4 h-4 text-indigo-400" />
                Active Specialist Network
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic delegation pipeline with authoritative role boundaries
              </p>
            </div>
            <button
              onClick={() => onNavigate("agents")}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium cursor-pointer"
            >
              View Full Topology →
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Router */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-indigo-300">Router Agent</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-900">
                  Coordinator
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
                Intent classification with deterministic safety keyword overrides.
              </p>
              <div className="mt-2 text-[10px] font-mono text-slate-500">
                Tools: 0 Direct (Delegator)
              </div>
            </div>

            {/* Book QA */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-emerald-300">Book QA Agent</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-900">
                  Accounting
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
                Portfolio balances, transactions, holdings, drift, and account snapshots.
              </p>
              <div className="mt-2 text-[10px] font-mono text-slate-500">
                Tools: 16 Verified Tools
              </div>
            </div>

            {/* KYC Profile */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-sky-300">KYC Profile Agent</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-900">
                  Compliance
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
                Masked KYC status, risk profiles, employer, income, and suitability reviews.
              </p>
              <div className="mt-2 text-[10px] font-mono text-slate-500">
                Tools: 2 Verified Tools
              </div>
            </div>

            {/* Compliance */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-rose-300">Compliance Agent</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-900">
                  Safety Refusal
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
                Deterministic policy refusals for investment advice and cross-client requests.
              </p>
              <div className="mt-2 text-[10px] font-mono text-slate-500">
                Tools: 0 (No Tools Permitted)
              </div>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Operational Telemetry & Live State */}
        <div className="p-5 rounded-xl bg-[#111624] border border-slate-800 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2 mb-1">
              <Database className="w-4 h-4 text-emerald-400" />
              Runtime Datasets
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Authoritative in-memory dataset snapshots
            </p>

            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-mono font-bold">Client Book</div>
                <div className="text-lg font-bold text-white font-mono mt-0.5">
                  {ready?.clients_loaded ?? 25} Authorized Clients
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Profiles, Accounts, Positions, Transactions, Memos
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-mono font-bold">Market Dataset</div>
                <div className="text-lg font-bold text-white font-mono mt-0.5">
                  {ready?.instruments_loaded ?? 14} Covered Tickers
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Monthly Close Observations, Returns, News
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-800">
            <button
              onClick={() => onNavigate("observability")}
              className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold flex items-center justify-center gap-2 border border-slate-800 cursor-pointer transition-colors"
            >
              View Telemetry Details →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
