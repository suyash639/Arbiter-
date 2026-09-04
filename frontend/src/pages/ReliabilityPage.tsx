import React, { useEffect, useState } from "react";
import { Activity, RefreshCw, Zap, CheckCircle2 } from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ReliabilitySummary } from "../api/types";

export const ReliabilityPage: React.FC = () => {
  const [rel, setRel] = useState<ReliabilitySummary | null>(null);

  useEffect(() => {
    arbiterApi.getReliabilitySummary().then(setRel).catch(() => {});
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <Activity className="w-5 h-5 text-indigo-400" />
          Reliability Engine & Fault Tolerance
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Upstream resilience with circuit breaking, exponential backoff jitter retries, and deterministic error categorization.
        </p>
      </div>

      {/* Grid of Key Reliability Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Retry Policy */}
        <div className="p-5 rounded-xl bg-[#111624] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold text-white uppercase font-mono">
            <span>Retry Policy</span>
            <RefreshCw className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between">
              <span className="text-slate-400">Max Attempts:</span>
              <span className="text-white font-bold">{rel?.max_attempts ?? 3}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Initial Backoff:</span>
              <span className="text-white">{rel?.initial_backoff_seconds ?? 1.0}s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Max Backoff:</span>
              <span className="text-white">{rel?.max_backoff_seconds ?? 8.0}s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Jitter:</span>
              <span className="text-emerald-400 font-semibold">Full Equal Jitter</span>
            </div>
          </div>
        </div>

        {/* Card 2: Circuit Breaker */}
        <div className="p-5 rounded-xl bg-[#111624] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold text-white uppercase font-mono">
            <span>Circuit Breaker</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Current State:</span>
              <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
                {rel?.circuit_breaker.state || "CLOSED"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Failure Threshold:</span>
              <span className="text-white">{rel?.circuit_breaker.failure_threshold ?? 5} failures</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Recovery Period:</span>
              <span className="text-white">{rel?.circuit_breaker.recovery_seconds ?? 30.0}s</span>
            </div>
          </div>
        </div>

        {/* Card 3: Timeout Protection */}
        <div className="p-5 rounded-xl bg-[#111624] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold text-white uppercase font-mono">
            <span>Timeout Budget</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between">
              <span className="text-slate-400">Per-Call Timeout:</span>
              <span className="text-white font-bold">{rel?.llm_timeout_seconds ?? 15.0}s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Threadpool Strategy:</span>
              <span className="text-white">Non-blocking ThreadPool</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Fallback Mode:</span>
              <span className="text-amber-400 font-semibold">Deterministic Envelope</span>
            </div>
          </div>
        </div>
      </div>

      {/* Non-Retryable Error Taxonomy */}
      <div className="p-5 rounded-xl bg-[#111624] border border-slate-800 space-y-3">
        <div className="text-xs font-bold text-white uppercase tracking-wider font-mono">
          Non-Retryable Classification Rules
        </div>
        <p className="text-xs text-slate-400">
          The following categories fail fast immediately without retry to protect backend safety and latency:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pt-1">
          {rel?.non_retryable_categories.map((cat, i) => (
            <div key={i} className="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
              ● {cat}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
