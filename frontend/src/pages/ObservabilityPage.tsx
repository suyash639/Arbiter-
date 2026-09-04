import React, { useEffect, useState } from "react";
import { BarChart3, RefreshCw } from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ObservabilitySummary } from "../api/types";

export const ObservabilityPage: React.FC = () => {
  const [obs, setObs] = useState<ObservabilitySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = () => {
    setLoading(true);
    arbiterApi.getObservabilitySummary()
      .then((data) => {
        setObs(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
            Observability & Execution Telemetry
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time in-memory request traces, latency percentiles, and structured multi-agent audit logs.
          </p>
        </div>

        <button
          onClick={loadData}
          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Traces</span>
        </button>
      </div>

      {/* Aggregate Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-3.5 rounded-xl bg-[#111624] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-slate-500">Total Requests</div>
          <div className="text-xl font-extrabold text-white font-mono mt-1">{obs?.total_requests ?? 0}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#111624] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-slate-500">Successful</div>
          <div className="text-xl font-extrabold text-emerald-400 font-mono mt-1">{obs?.successful_requests ?? 0}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#111624] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-slate-500">Refused</div>
          <div className="text-xl font-extrabold text-rose-400 font-mono mt-1">{obs?.refused_requests ?? 0}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#111624] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-slate-500">Abstained</div>
          <div className="text-xl font-extrabold text-amber-400 font-mono mt-1">{obs?.abstained_requests ?? 0}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#111624] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-slate-500">P50 Latency</div>
          <div className="text-xl font-extrabold text-indigo-400 font-mono mt-1">
            {obs?.p50_latency_ms ? `${obs.p50_latency_ms.toFixed(1)}ms` : "0.0ms"}
          </div>
        </div>
        <div className="p-3.5 rounded-xl bg-[#111624] border border-slate-800">
          <div className="text-[10px] uppercase font-mono font-bold text-slate-500">P95 Latency</div>
          <div className="text-xl font-extrabold text-indigo-400 font-mono mt-1">
            {obs?.p95_latency_ms ? `${obs.p95_latency_ms.toFixed(1)}ms` : "0.0ms"}
          </div>
        </div>
      </div>

      {/* Recent Request Traces Table */}
      <div className="rounded-xl bg-[#111624] border border-slate-800 overflow-hidden shadow-lg space-y-2">
        <div className="px-4 py-3 border-b border-slate-800 text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
          Recent Executed Request Traces ({obs?.recent_traces.length ?? 0})
        </div>

        {obs?.recent_traces.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 font-mono">
            No request traces recorded yet in memory buffer. Submit queries via Ask Arbiter to view live telemetry.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">Request ID</th>
                  <th className="py-2.5 px-4">Client</th>
                  <th className="py-2.5 px-4">Agent Path</th>
                  <th className="py-2.5 px-4">Tools</th>
                  <th className="py-2.5 px-4">Total Latency</th>
                  <th className="py-2.5 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200 font-mono">
                {obs?.recent_traces.map((tr) => (
                  <tr key={tr.request_id} className="hover:bg-slate-900/50">
                    <td className="py-2.5 px-4 text-indigo-400 font-bold">{tr.request_id}</td>
                    <td className="py-2.5 px-4 text-slate-300">{tr.client_id}</td>
                    <td className="py-2.5 px-4">
                      <div className="flex items-center gap-1 text-[11px]">
                        {tr.agent_path.map((ag, i) => (
                          <span key={i} className="flex items-center gap-1">
                            <span className="text-indigo-300 font-semibold">{ag}</span>
                            {i < tr.agent_path.length - 1 && <span className="text-slate-600">→</span>}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-2.5 px-4">{tr.tool_call_count} calls</td>
                    <td className="py-2.5 px-4 text-slate-300">
                      {tr.total_latency_ms ? `${tr.total_latency_ms} ms` : "—"}
                    </td>
                    <td className="py-2.5 px-4">
                      {tr.refused ? (
                        <span className="text-rose-400 font-bold">REFUSED</span>
                      ) : tr.abstained ? (
                        <span className="text-amber-400 font-bold">ABSTAINED</span>
                      ) : tr.success ? (
                        <span className="text-emerald-400 font-bold">SUCCESS</span>
                      ) : (
                        <span className="text-rose-400 font-bold">ERROR</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
