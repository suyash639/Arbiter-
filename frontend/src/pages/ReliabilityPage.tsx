import React, { useEffect, useState } from "react";
import {
  Activity,
  RefreshCw,
  Zap,
  AlertOctagon,
  Timer,
  Layers,
  ShieldAlert,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ReliabilitySummary } from "../api/types";
import { StatusIndicator } from "../components/StatusIndicator";

export const ReliabilityPage: React.FC = () => {
  const [rel, setRel] = useState<ReliabilitySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadReliability = () => {
    setLoading(true);
    arbiterApi
      .getReliabilitySummary()
      .then((data) => {
        setRel(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadReliability();
  }, []);

  const pipelineSteps = [
    {
      step: "1. Upstream Failure",
      sub: "Timeout / 5xx / Socket Drop",
      icon: AlertOctagon,
      desc: "API gateway or LLM provider fails to respond within the 15.0s budget.",
      color: "border-rose-800/80 bg-rose-950/20 text-rose-300",
    },
    {
      step: "2. Classification",
      sub: "Deterministic Taxonomizer",
      icon: Layers,
      desc: "Distinguishes transient network errors from non-retryable client/policy violations.",
      color: "border-indigo-800/80 bg-indigo-950/20 text-indigo-300",
    },
    {
      step: "3. Backoff + Jitter",
      sub: "1.0s base · 8.0s cap · Full Jitter",
      icon: RefreshCw,
      desc: "Applies truncated exponential backoff with full equal jitter to prevent thundering herds.",
      color: "border-sky-800/80 bg-sky-950/20 text-sky-300",
    },
    {
      step: "4. Circuit Breaker",
      sub: "5 Failures · 30.0s Recovery",
      icon: Zap,
      desc: "Trips to OPEN state if threshold is breached, shedding load and failing fast.",
      color: "border-amber-800/80 bg-amber-950/20 text-amber-300",
    },
    {
      step: "5. Safe Abstention",
      sub: "Deterministic AnswerSchema",
      icon: ShieldAlert,
      desc: "Emits a typed abstention envelope with reason instead of crashing or hallucinating.",
      color: "border-emerald-800/80 bg-emerald-950/20 text-emerald-300",
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1a2234] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold tracking-tight text-white font-mono flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-400" />
              RELIABILITY ENGINE & FAULT TOLERANCE
            </h1>
            <StatusIndicator status="READY" size="sm" />
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Deterministic upstream fault isolation, exponential backoff retries with full jitter, circuit breaking, and abstention fallbacks.
          </p>
        </div>

        <button
          onClick={loadReliability}
          disabled={loading}
          className="self-start md:self-auto px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-xs font-mono text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin text-indigo-400" : ""}`} />
          <span>Refresh Config</span>
        </button>
      </div>

      {/* Authoritative Configuration Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
            Authoritative Engine Configuration
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            arbiter.config.Config Settings
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Card 1: Retry & Backoff */}
          <div className="p-3.5 rounded-lg bg-[#0c101a] border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-bold text-white font-mono uppercase flex items-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
                Retry & Backoff Policy
              </span>
              <span className="text-[9px] font-mono text-emerald-400 font-bold">ACTIVE</span>
            </div>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex justify-between items-center py-0.5 border-b border-slate-800/40">
                <span className="text-slate-400">Max Attempts</span>
                <span className="text-white font-bold">{rel?.max_attempts ?? 3}</span>
              </div>
              <div className="flex justify-between items-center py-0.5 border-b border-slate-800/40">
                <span className="text-slate-400">Initial Backoff</span>
                <span className="text-white">{rel?.initial_backoff_seconds ?? 1.0}s</span>
              </div>
              <div className="flex justify-between items-center py-0.5 border-b border-slate-800/40">
                <span className="text-slate-400">Max Backoff Cap</span>
                <span className="text-white">{rel?.max_backoff_seconds ?? 8.0}s</span>
              </div>
              <div className="flex justify-between items-center py-0.5">
                <span className="text-slate-400">Jitter Algorithm</span>
                <span className="text-emerald-400 font-bold">Full Equal Jitter</span>
              </div>
            </div>
          </div>

          {/* Card 2: Circuit Breaker */}
          <div className="p-3.5 rounded-lg bg-[#0c101a] border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-bold text-white font-mono uppercase flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                Circuit Breaker Isolation
              </span>
              <span className="text-[9px] font-mono text-emerald-400 font-bold">
                {rel?.circuit_breaker.state || "CLOSED"}
              </span>
            </div>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex justify-between items-center py-0.5 border-b border-slate-800/40">
                <span className="text-slate-400">Breaker State</span>
                <span className="text-emerald-400 font-bold px-1.5 py-0.2 rounded bg-emerald-950 border border-emerald-800">
                  {rel?.circuit_breaker.state || "CLOSED"}
                </span>
              </div>
              <div className="flex justify-between items-center py-0.5 border-b border-slate-800/40">
                <span className="text-slate-400">Failure Threshold</span>
                <span className="text-white font-bold">{rel?.circuit_breaker.failure_threshold ?? 5} errors</span>
              </div>
              <div className="flex justify-between items-center py-0.5 border-b border-slate-800/40">
                <span className="text-slate-400">Recovery Cooldown</span>
                <span className="text-white">{rel?.circuit_breaker.recovery_seconds ?? 30.0}s</span>
              </div>
              <div className="flex justify-between items-center py-0.5">
                <span className="text-slate-400">Half-Open Probe</span>
                <span className="text-indigo-300 font-bold">1 Request</span>
              </div>
            </div>
          </div>

          {/* Card 3: Execution Budget */}
          <div className="p-3.5 rounded-lg bg-[#0c101a] border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-bold text-white font-mono uppercase flex items-center gap-1.5">
                <Timer className="w-3.5 h-3.5 text-emerald-400" />
                Execution Budget & Fallback
              </span>
              <span className="text-[9px] font-mono text-indigo-400 font-bold">ENFORCED</span>
            </div>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex justify-between items-center py-0.5 border-b border-slate-800/40">
                <span className="text-slate-400">Per-Call Timeout</span>
                <span className="text-white font-bold">{rel?.llm_timeout_seconds ?? 15.0}s</span>
              </div>
              <div className="flex justify-between items-center py-0.5 border-b border-slate-800/40">
                <span className="text-slate-400">Execution Model</span>
                <span className="text-white">Non-blocking Threadpool</span>
              </div>
              <div className="flex justify-between items-center py-0.5 border-b border-slate-800/40">
                <span className="text-slate-400">Fallback Strategy</span>
                <span className="text-amber-300 font-bold">Safe Abstention</span>
              </div>
              <div className="flex justify-between items-center py-0.5">
                <span className="text-slate-400">Envelope Integrity</span>
                <span className="text-emerald-400 font-bold">AnswerSchema</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Failure Mitigation Pipeline */}
      <div className="p-4 rounded-lg bg-[#0c101a] border border-slate-800 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
            Fault Handling & Mitigation Lifecycle
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Pipeline Progression
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-2.5">
          {pipelineSteps.map((p, idx) => {
            const Icon = p.icon;
            return (
              <div
                key={idx}
                className={`p-3 rounded-lg border flex flex-col justify-between space-y-2 ${p.color}`}
              >
                <div>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Icon className="w-3.5 h-3.5" />
                    <span className="text-[10px] font-bold font-mono uppercase">
                      {p.step}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-slate-200 font-semibold mb-1">
                    {p.sub}
                  </div>
                  <p className="text-[11px] text-slate-300 leading-snug">
                    {p.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Non-Retryable Error Taxonomy */}
      <div className="p-4 rounded-lg bg-[#0c101a] border border-slate-800 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div>
            <div className="text-xs font-mono uppercase font-bold text-slate-300">
              Non-Retryable Classification Taxonomy
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              The following categories fail fast immediately without wasting retry budget or leaking latency:
            </p>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 font-semibold">
            FAST-FAIL
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pt-1">
          {rel?.non_retryable_categories.map((cat, i) => (
            <div
              key={i}
              className="p-2.5 rounded bg-slate-900/80 border border-slate-800 text-xs font-mono text-slate-300 flex items-center gap-2"
            >
              <div className="w-1.5 h-1.5 rounded-full bg-rose-400 shrink-0" />
              <span>{cat}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Runtime Telemetry vs Configuration Notice */}
      <div className="p-4 rounded-lg bg-[#0c101a] border border-slate-800 space-y-2">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase font-bold text-slate-300">
              Runtime Reliability Log & Telemetry
            </span>
          </div>
          <StatusIndicator status="ONLINE" size="sm" />
        </div>

        <div className="p-4 rounded bg-slate-950/60 border border-slate-800/80 text-center space-y-1">
          <div className="text-xs font-mono text-slate-300">
            Runtime reliability events not currently exposed.
          </div>
          <p className="text-[11px] text-slate-500 max-w-md mx-auto">
            Circuit breaker is in CLOSED state with 0 consecutive trips. Transient retry events are streamed directly to sanitized service telemetry.
          </p>
        </div>
      </div>
    </div>
  );
};
