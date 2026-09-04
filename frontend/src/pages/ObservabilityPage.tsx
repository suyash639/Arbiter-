import React, { useEffect, useState } from "react";
import {
  BarChart3,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ObservabilitySummary, TraceSummary } from "../api/types";
import { StatusIndicator } from "../components/StatusIndicator";
import { EmptyState } from "../components/EmptyState";

interface ObservabilityPageProps {
  onNavigate?: (page: string) => void;
}

export const ObservabilityPage: React.FC<ObservabilityPageProps> = ({ onNavigate }) => {
  const [obs, setObs] = useState<ObservabilitySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    arbiterApi
      .getObservabilitySummary()
      .then((data) => {
        setObs(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const toggleExpand = (reqId: string) => {
    setExpandedTraceId(expandedTraceId === reqId ? null : reqId);
  };

  const formatLatency = (ms: number | null | undefined) => {
    if (ms === null || ms === undefined) return "—";
    return `${ms.toFixed(1)} ms`;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1a2234] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold tracking-tight text-white font-mono flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-indigo-400" />
              OBSERVABILITY & REQUEST TELEMETRY
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/40 text-indigo-300 border border-indigo-800/60 font-semibold">
              IN-MEMORY COLLECTOR
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time in-memory request traces, latency percentiles, agent path transitions, and tool invocation counts.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="self-start md:self-auto px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-xs font-mono text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin text-indigo-400" : ""}`} />
          <span>Refresh Traces</span>
        </button>
      </div>

      {/* Aggregate Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        <div className="p-3 rounded-lg bg-[#0c101a] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-slate-400">Total Requests</div>
          <div className="text-lg font-bold text-white font-mono mt-0.5">
            {obs?.total_requests ?? 0}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-[#0c101a] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-emerald-400">Successful</div>
          <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">
            {obs?.successful_requests ?? 0}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-[#0c101a] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-rose-400">Refused</div>
          <div className="text-lg font-bold text-rose-400 font-mono mt-0.5">
            {obs?.refused_requests ?? 0}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-[#0c101a] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-amber-400">Abstained</div>
          <div className="text-lg font-bold text-amber-400 font-mono mt-0.5">
            {obs?.abstained_requests ?? 0}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-[#0c101a] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-indigo-400">P50 Latency</div>
          <div className="text-lg font-bold text-indigo-300 font-mono mt-0.5">
            {obs?.p50_latency_ms ? `${obs.p50_latency_ms.toFixed(1)} ms` : "—"}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-[#0c101a] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-purple-400">P95 Latency</div>
          <div className="text-lg font-bold text-purple-300 font-mono mt-0.5">
            {obs?.p95_latency_ms ? `${obs.p95_latency_ms.toFixed(1)} ms` : "—"}
          </div>
        </div>
      </div>

      {/* Recent Request Traces Table */}
      <div className="rounded-lg bg-[#0c101a] border border-slate-800 overflow-hidden shadow-sm">
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="text-xs font-mono uppercase font-bold text-slate-300">
            Recent Request Traces ({obs?.recent_traces.length ?? 0})
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Click row to inspect timing & specialist breakdown
          </span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs font-mono text-slate-400">
            Loading telemetry traces...
          </div>
        ) : !obs || obs.recent_traces.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No requests recorded yet"
            description="Execute queries via Ask Arbiter or submit API requests to view live end-to-end telemetry traces."
            actionLabel={onNavigate ? "Open Ask Arbiter" : undefined}
            onAction={onNavigate ? () => onNavigate("ask") : undefined}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">Request ID</th>
                  <th className="py-2.5 px-4">Client Scope</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Agent Path</th>
                  <th className="py-2.5 px-4">Tools</th>
                  <th className="py-2.5 px-4">Total Latency</th>
                  <th className="py-2.5 px-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {obs.recent_traces.map((tr: TraceSummary) => {
                  const isExpanded = expandedTraceId === tr.request_id;
                  return (
                    <React.Fragment key={tr.request_id}>
                      <tr
                        onClick={() => toggleExpand(tr.request_id)}
                        className={`hover:bg-slate-800/40 cursor-pointer transition-colors ${
                          isExpanded ? "bg-slate-800/30" : ""
                        }`}
                      >
                        <td className="py-3 px-4 text-indigo-400 font-bold">
                          {tr.request_id}
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {tr.client_id}
                        </td>
                        <td className="py-3 px-4">
                          <StatusIndicator
                            status={tr.refused ? "REFUSED" : tr.abstained ? "ABSTAINED" : tr.success ? "SUCCESS" : "ERROR"}
                            size="sm"
                          />
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-1 text-[11px]">
                            {(tr.agent_path || []).map((ag: string, i: number, arr: string[]) => (
                              <span key={i} className="flex items-center gap-1">
                                <span className="text-slate-200">{ag}</span>
                                {i < arr.length - 1 && (
                                  <span className="text-slate-600">→</span>
                                )}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {tr.tool_call_count} calls
                        </td>
                        <td className="py-3 px-4 text-slate-200">
                          {formatLatency(tr.total_latency_ms)}
                        </td>
                        <td className="py-3 px-4 text-right text-slate-500">
                          {isExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5 inline" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 inline" />
                          )}
                        </td>
                      </tr>

                      {/* Expanded Trace Breakdown */}
                      {isExpanded && (
                        <tr className="bg-slate-950/80 border-b border-slate-800">
                          <td colSpan={7} className="p-4 space-y-3">
                            <div className="text-xs font-mono uppercase font-bold text-slate-400 mb-2">
                              Execution Breakdown — {tr.request_id}
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
                              <div className="p-2.5 rounded bg-slate-900 border border-slate-800 space-y-1">
                                <span className="text-slate-500 text-[10px] uppercase block">Provider & Model</span>
                                <span className="text-slate-200 font-bold">{tr.provider} / {tr.model}</span>
                              </div>
                              <div className="p-2.5 rounded bg-slate-900 border border-slate-800 space-y-1">
                                <span className="text-slate-500 text-[10px] uppercase block">Router Latency</span>
                                <span className="text-indigo-300 font-bold">{formatLatency(tr.router_latency_ms)}</span>
                              </div>
                              <div className="p-2.5 rounded bg-slate-900 border border-slate-800 space-y-1">
                                <span className="text-slate-500 text-[10px] uppercase block">Specialist Latency</span>
                                <span className="text-emerald-300 font-bold">{formatLatency(tr.specialist_latency_ms)}</span>
                              </div>
                              <div className="p-2.5 rounded bg-slate-900 border border-slate-800 space-y-1">
                                <span className="text-slate-500 text-[10px] uppercase block">Question ID</span>
                                <span className="text-slate-300">{tr.question_id || "adhoc_query"}</span>
                              </div>
                            </div>
                            {tr.error && (
                              <div className="p-2.5 rounded bg-rose-950/40 border border-rose-800 text-rose-300 text-xs font-mono">
                                <strong>Error:</strong> {tr.error}
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
