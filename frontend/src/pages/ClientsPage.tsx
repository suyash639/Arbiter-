import React, { useEffect, useState } from "react";
import {
  Users,
  Search,
  ArrowRight,
  RefreshCw,
  UserCheck,
  Lock,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ClientSummary } from "../api/types";
import type { NavPage } from "../components/Shell";
import { EmptyState } from "../components/EmptyState";

interface ClientsPageProps {
  onSelectClient?: (clientId: string) => void;
  onNavigate?: (page: NavPage) => void;
}

export const ClientsPage: React.FC<ClientsPageProps> = ({ onSelectClient, onNavigate }) => {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");
  const [selectedRisk, setSelectedRisk] = useState<string>("all");
  const [activeClientId, setActiveClientId] = useState<string | null>(null);

  const loadClients = () => {
    setLoading(true);
    arbiterApi
      .getClients()
      .then((data) => {
        setClients(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadClients();
  }, []);

  const filteredClients = clients.filter((c) => {
    const matchesSearch =
      c.client_id.toLowerCase().includes(search.toLowerCase()) ||
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.risk_profile.toLowerCase().includes(search.toLowerCase());

    const matchesRisk =
      selectedRisk === "all" ||
      c.risk_profile.toLowerCase().includes(selectedRisk.toLowerCase()) ||
      c.target_risk.toLowerCase().includes(selectedRisk.toLowerCase());

    return matchesSearch && matchesRisk;
  });

  const handleSelectClient = (clientId: string) => {
    setActiveClientId(clientId);
    if (onSelectClient) {
      onSelectClient(clientId);
    }
  };

  const handleQueryClient = (clientId: string) => {
    handleSelectClient(clientId);
    if (onNavigate) {
      onNavigate("ask");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1a2234] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold tracking-tight text-white font-mono flex items-center gap-2">
              <Users className="w-4 h-4 text-emerald-400" />
              CLIENT PORTFOLIO BOOK
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/60 font-semibold">
              {clients.length} AUTHORIZED RECORDS
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Authoritative directory of client portfolios. Select a client to bound operations context before submitting queries.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeClientId && (
            <div className="px-2.5 py-1 rounded bg-[#0c101a] border border-indigo-800/60 text-xs font-mono flex items-center gap-1.5">
              <span className="text-slate-500">CONTEXT:</span>
              <span className="text-indigo-300 font-bold">{activeClientId}</span>
            </div>
          )}
          <button
            onClick={loadClients}
            disabled={loading}
            className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-xs font-mono text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin text-emerald-400" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search by client ID, name, or risk profile..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded bg-[#0c101a] border border-slate-800 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>

        {/* Risk Profile Filter Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-mono uppercase font-bold text-slate-500 mr-1">
            Risk:
          </span>
          {["all", "conservative", "moderate", "aggressive"].map((r) => (
            <button
              key={r}
              onClick={() => setSelectedRisk(r)}
              className={`px-2.5 py-1 rounded text-xs font-mono capitalize transition-colors cursor-pointer ${
                selectedRisk === r
                  ? "bg-indigo-600 text-white font-semibold"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              {r === "all" ? `All (${clients.length})` : r}
            </button>
          ))}
        </div>
      </div>

      {/* Security Context Strip */}
      <div className="p-2.5 rounded bg-[#0c101a] border border-slate-800/80 flex items-center justify-between text-[11px] font-mono">
        <div className="flex items-center gap-2 text-slate-400">
          <Lock className="w-3.5 h-3.5 text-indigo-400" />
          <span>
            Cross-Client Isolation: <strong className="text-emerald-400">ENFORCED</strong>
          </span>
        </div>
        <span className="text-slate-500 text-[10px]">
          Deterministic closure boundaries isolate data storage access
        </span>
      </div>

      {/* Clients Operations Table */}
      <div className="rounded-lg bg-[#0c101a] border border-slate-800 overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs font-mono text-slate-400">
            Loading client book...
          </div>
        ) : filteredClients.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No client records found"
            description={
              search || selectedRisk !== "all"
                ? "No client records match your current search or risk filter."
                : "No client records available in the authoritative DataStore."
            }
            actionLabel={search || selectedRisk !== "all" ? "Reset Filters" : undefined}
            onAction={() => {
              setSearch("");
              setSelectedRisk("all");
            }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">Client ID</th>
                  <th className="py-2.5 px-4">Client Name</th>
                  <th className="py-2.5 px-4">Risk Profile</th>
                  <th className="py-2.5 px-4">KYC Status</th>
                  <th className="py-2.5 px-4">Accounts</th>
                  <th className="py-2.5 px-4">Target Risk</th>
                  <th className="py-2.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {filteredClients.map((c) => {
                  const isSelected = activeClientId === c.client_id;
                  return (
                    <tr
                      key={c.client_id}
                      onClick={() => handleSelectClient(c.client_id)}
                      className={`hover:bg-slate-800/40 transition-colors cursor-pointer ${
                        isSelected ? "bg-indigo-950/20" : ""
                      }`}
                    >
                      <td className="py-2.5 px-4 font-mono font-bold text-indigo-400">
                        {c.client_id}
                      </td>
                      <td className="py-2.5 px-4 font-medium text-slate-200">
                        {c.name}
                      </td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                          {c.risk_profile}
                        </span>
                      </td>
                      <td className="py-2.5 px-4">
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-mono">
                          <UserCheck className="w-3 h-3" />
                          {c.kyc_status}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono text-slate-300">
                        {c.accounts_count} accounts
                      </td>
                      <td className="py-2.5 px-4 text-slate-400 font-mono text-[11px]">
                        {c.target_risk}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleQueryClient(c.client_id);
                          }}
                          className="px-2.5 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/40 font-mono font-semibold text-[11px] inline-flex items-center gap-1 transition-all cursor-pointer"
                        >
                          <span>Query</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
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
