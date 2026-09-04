import React, { useEffect, useState } from "react";
import {
  Wrench,
  Search,
  CheckCircle2,
  RefreshCw,
  Lock,
  ChevronDown,
  ChevronUp,
  Globe,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ToolSummary } from "../api/types";
import { EmptyState } from "../components/EmptyState";

export const ToolsPage: React.FC = () => {
  const [tools, setTools] = useState<ToolSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");
  const [selectedAgent, setSelectedAgent] = useState<string>("all");
  const [expandedToolName, setExpandedToolName] = useState<string | null>(null);

  const loadTools = () => {
    setLoading(true);
    arbiterApi
      .getTools()
      .then((data) => {
        setTools(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadTools();
  }, []);

  const toggleExpand = (name: string) => {
    setExpandedToolName(expandedToolName === name ? null : name);
  };

  const domainFilters = [
    { id: "all", label: "All (24)" },
    { id: "book_qa", label: "Book QA (16)" },
    { id: "market_desk", label: "Market Desk (4)" },
    { id: "kyc_profile", label: "KYC Profile (2)" },
    { id: "notes_desk", label: "Notes Desk (2)" },
    { id: "compliance", label: "Compliance (0)" },
  ];

  const filteredTools = tools.filter((t) => {
    const matchesSearch =
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase()) ||
      t.argument_schema.toLowerCase().includes(search.toLowerCase());

    const matchesAgent =
      selectedAgent === "all" ||
      (selectedAgent === "compliance"
        ? false
        : t.owning_agents.includes(selectedAgent));

    return matchesSearch && matchesAgent;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1a2234] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold tracking-tight text-white font-mono flex items-center gap-2">
              <Wrench className="w-4 h-4 text-sky-400" />
              VERIFIED TOOL REGISTRY
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950/40 text-sky-300 border border-sky-800/60 font-semibold">
              {tools.length} REGISTERED DETERMINISTIC TOOLS
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Authoritative registry of financial tools with Pydantic argument schemas, client scope isolation, and explicit agent allowlists.
          </p>
        </div>

        <button
          onClick={loadTools}
          disabled={loading}
          className="self-start md:self-auto px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-xs font-mono text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin text-sky-400" : ""}`} />
          <span>Refresh Registry</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search by tool name, argument schema, or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded bg-[#0c101a] border border-slate-800 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>

        {/* Domain Specialist Filters */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-mono uppercase font-bold text-slate-500 mr-1">
            Owner:
          </span>
          {domainFilters.map((df) => (
            <button
              key={df.id}
              onClick={() => setSelectedAgent(df.id)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-colors cursor-pointer ${
                selectedAgent === df.id
                  ? "bg-indigo-600 text-white font-semibold"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              {df.label}
            </button>
          ))}
        </div>
      </div>

      {/* Security Notice */}
      <div className="p-2.5 rounded bg-[#0c101a] border border-slate-800/80 flex items-center justify-between text-[11px] font-mono">
        <div className="flex items-center gap-2 text-slate-400">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>
            Tool Verification Layer: <strong className="text-emerald-400">ACTIVE</strong>
          </span>
        </div>
        <span className="text-slate-500 text-[10px]">
          Pre-execution schema validation & scope bounds strictly enforced
        </span>
      </div>

      {/* Tools Table */}
      <div className="rounded-lg bg-[#0c101a] border border-slate-800 overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs font-mono text-slate-400">
            Loading verified tool registry...
          </div>
        ) : filteredTools.length === 0 ? (
          <EmptyState
            icon={Wrench}
            title={selectedAgent === "compliance" ? "Compliance agent has zero tools" : "No tools found"}
            description={
              selectedAgent === "compliance"
                ? "The Compliance agent is intentionally configured with 0 tools to guarantee deterministic policy refusal for investment advice."
                : "No registered tools match your search query."
            }
            actionLabel={selectedAgent !== "all" || search ? "Reset Filters" : undefined}
            onAction={() => {
              setSelectedAgent("all");
              setSearch("");
            }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">Tool Name</th>
                  <th className="py-2.5 px-4">Owning Agents</th>
                  <th className="py-2.5 px-4">Scope</th>
                  <th className="py-2.5 px-4">Argument Schema</th>
                  <th className="py-2.5 px-4">Return Shape</th>
                  <th className="py-2.5 px-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-200">
                {filteredTools.map((tool) => {
                  const isExpanded = expandedToolName === tool.name;
                  return (
                    <React.Fragment key={tool.name}>
                      <tr
                        onClick={() => toggleExpand(tool.name)}
                        className={`hover:bg-slate-800/40 cursor-pointer transition-colors ${
                          isExpanded ? "bg-slate-800/30" : ""
                        }`}
                      >
                        <td className="py-3 px-4 font-bold text-sky-300">
                          {tool.name}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap gap-1">
                            {tool.owning_agents.map((ag) => (
                              <span
                                key={ag}
                                className="px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60 text-[10px]"
                              >
                                {ag}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          {tool.is_client_scoped ? (
                            <span className="inline-flex items-center gap-1 text-emerald-400 text-[11px]">
                              <Lock className="w-3 h-3 text-emerald-500" />
                              Client Scope
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-purple-400 text-[11px]">
                              <Globe className="w-3 h-3 text-purple-500" />
                              Global Market
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {tool.argument_schema}
                        </td>
                        <td className="py-3 px-4 text-slate-400 text-[11px]">
                          {tool.expected_shape}
                        </td>
                        <td className="py-3 px-4 text-right text-slate-500">
                          {isExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5 inline" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 inline" />
                          )}
                        </td>
                      </tr>

                      {/* Expandable Details Row */}
                      {isExpanded && (
                        <tr className="bg-slate-950/80 border-b border-slate-800">
                          <td colSpan={6} className="p-4 space-y-2">
                            <div className="text-[10px] font-mono uppercase font-bold text-slate-400">
                              Tool Description & Specification
                            </div>
                            <p className="text-xs text-slate-300 leading-relaxed font-sans">
                              {tool.description}
                            </p>
                            <div className="pt-2 flex items-center gap-3 text-[11px] font-mono text-slate-400">
                              <span>Verification: <strong className="text-emerald-400 font-bold">STRICT PYDANTIC</strong></span>
                              <span>•</span>
                              <span>Arithmetic: <strong className="text-emerald-400 font-bold">100% DECIMAL</strong></span>
                              <span>•</span>
                              <span>Citations: <strong className="text-indigo-300 font-bold">MANDATORY RECORD ID</strong></span>
                            </div>
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
