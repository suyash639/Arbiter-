import React, { useEffect, useState } from "react";
import { Network, ArrowDown } from "lucide-react";
import { arbiterApi } from "../api/client";
import type { AgentSummary } from "../api/types";

export const AgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentSummary[]>([]);

  useEffect(() => {
    arbiterApi.getAgents().then(setAgents).catch(() => {});
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <Network className="w-5 h-5 text-indigo-400" />
          Agent Network & Specialist Topology
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Deterministic coordinator and specialist agents with isolated domain responsibilities and declarative tool boundaries.
        </p>
      </div>

      {/* Top Architecture Topology Diagram */}
      <div className="p-6 rounded-xl bg-[#111624] border border-slate-800 text-center relative overflow-hidden">
        <div className="text-[10px] font-mono uppercase font-bold text-slate-500 tracking-wider mb-4">
          Hierarchical Delegation Workflow
        </div>

        {/* Router Box */}
        <div className="inline-block p-4 rounded-xl bg-indigo-950/60 border border-indigo-500/50 shadow-lg text-left max-w-sm w-full mx-auto">
          <div className="flex items-center justify-between">
            <span className="font-extrabold text-xs text-indigo-300">Router Coordinator</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-900 text-indigo-200 border border-indigo-700">
              Entry Gateway
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Classifies user intent & enforces deterministic compliance overrides.
          </p>
        </div>

        {/* Down Arrow */}
        <div className="my-3 flex justify-center text-slate-600">
          <ArrowDown className="w-5 h-5 animate-bounce text-indigo-400" />
        </div>

        {/* Specialist Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 max-w-5xl mx-auto">
          <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-left">
            <div className="font-bold text-xs text-emerald-300">Book QA</div>
            <div className="text-[10px] text-slate-400 mt-0.5">16 Tools</div>
          </div>
          <div className="p-3 rounded-lg bg-sky-950/40 border border-sky-800/60 text-left">
            <div className="font-bold text-xs text-sky-300">KYC Profile</div>
            <div className="text-[10px] text-slate-400 mt-0.5">2 Tools</div>
          </div>
          <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/60 text-left">
            <div className="font-bold text-xs text-amber-300">Notes Desk</div>
            <div className="text-[10px] text-slate-400 mt-0.5">2 Tools</div>
          </div>
          <div className="p-3 rounded-lg bg-purple-950/40 border border-purple-800/60 text-left">
            <div className="font-bold text-xs text-purple-300">Market Desk</div>
            <div className="text-[10px] text-slate-400 mt-0.5">4 Tools</div>
          </div>
          <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-left">
            <div className="font-bold text-xs text-rose-300">Compliance</div>
            <div className="text-[10px] text-slate-400 mt-0.5">0 Tools (Refusal)</div>
          </div>
        </div>
      </div>

      {/* Agents Detailed Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="p-5 rounded-xl bg-[#111624] border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition-all shadow-md"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="font-extrabold text-sm text-white">{agent.name}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-indigo-300 font-bold">
                  {agent.id}
                </span>
              </div>
              <div className="text-xs font-semibold text-indigo-400 mt-1">{agent.role}</div>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">{agent.description}</p>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-500">Tool Authority:</span>
              <span
                className={`font-bold ${
                  agent.tool_count > 0 ? "text-emerald-400" : "text-slate-400"
                }`}
              >
                {agent.tool_count} {agent.tool_count === 1 ? "Tool" : "Tools"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
