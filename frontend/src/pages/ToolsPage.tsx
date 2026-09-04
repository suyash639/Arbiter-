import React, { useEffect, useState } from "react";
import { Wrench, Search, Lock } from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ToolSummary } from "../api/types";

export const ToolsPage: React.FC = () => {
  const [tools, setTools] = useState<ToolSummary[]>([]);
  const [search, setSearch] = useState<string>("");
  const [selectedAgent, setSelectedAgent] = useState<string>("all");

  useEffect(() => {
    arbiterApi.getTools().then(setTools).catch(() => {});
  }, []);

  const filtered = tools.filter((t) => {
    const matchesSearch =
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase());
    const matchesAgent =
      selectedAgent === "all" || t.owning_agents.includes(selectedAgent);
    return matchesSearch && matchesAgent;
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Wrench className="w-5 h-5 text-indigo-400" />
            Verified Tool Registry (24 Deterministic Tools)
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Strict agent-to-tool authorization, Pydantic argument validation, and result verification before model exposure.
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          >
            <option value="all">All Agents (24)</option>
            <option value="book_qa">Book QA (16)</option>
            <option value="market_desk">Market Desk (4)</option>
            <option value="kyc_profile">KYC Profile (2)</option>
            <option value="notes_desk">Notes Desk (2)</option>
          </select>

          <div className="relative w-48">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tools..."
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>
      </div>

      {/* Tools Table */}
      <div className="rounded-xl bg-[#111624] border border-slate-800 overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Tool Name</th>
                <th className="py-3 px-4">Owning Agents</th>
                <th className="py-3 px-4">Scope Enforced</th>
                <th className="py-3 px-4">Argument Schema</th>
                <th className="py-3 px-4">Return Shape</th>
                <th className="py-3 px-4">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {filtered.map((tool) => (
                <tr key={tool.name} className="hover:bg-slate-900/50 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-amber-400">
                    {tool.name}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex flex-wrap gap-1">
                      {tool.owning_agents.map((ag) => (
                        <span
                          key={ag}
                          className="px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono text-[10px]"
                        >
                          {ag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-4 font-mono">
                    {tool.is_client_scoped ? (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400">
                        <Lock className="w-3 h-3" />
                        Client Scoped
                      </span>
                    ) : (
                      <span className="text-slate-500 text-[11px]">Global Scope</span>
                    )}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-300 text-[11px]">
                    {tool.argument_schema}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">
                    {tool.expected_shape}
                  </td>
                  <td className="py-3 px-4 text-slate-400 max-w-xs truncate">
                    {tool.description}
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
