import React, { useEffect, useState } from "react";
import { Users, UserCheck, ArrowRight, Search, Lock, Loader2 } from "lucide-react";
import { arbiterApi } from "../api/client";
import type { ClientSummary } from "../api/types";
import type { NavPage } from "../components/Shell";

interface ClientsPageProps {
  onSelectClient: (clientId: string) => void;
  onNavigate: (page: NavPage) => void;
}

export const ClientsPage: React.FC<ClientsPageProps> = ({
  onSelectClient,
  onNavigate,
}) => {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [search, setSearch] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    arbiterApi.getClients()
      .then((cls) => {
        setClients(cls);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filtered = clients.filter(
    (c) =>
      c.client_id.toLowerCase().includes(search.toLowerCase()) ||
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.risk_profile.toLowerCase().includes(search.toLowerCase())
  );

  const handleLaunchQuery = (cid: string) => {
    onSelectClient(cid);
    onNavigate("ask");
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" />
            Client Book Operations Directory
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Authorized client portfolio scopes with context-enforced data boundaries and masked PII.
          </p>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by ID, name, risk..."
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
      </div>

      {/* Security Banner */}
      <div className="p-3.5 rounded-lg bg-indigo-950/40 border border-indigo-800/60 text-indigo-200 text-xs flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Lock className="w-4 h-4 text-indigo-400 shrink-0" />
          <span>
            <strong>Client Isolation Guarantee:</strong> Queries to specialist agents strictly enforce pre-flight client authorization against the authoritative DataStore.
          </span>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-900 text-indigo-200 border border-indigo-700">
          PII MASKED
        </span>
      </div>

      {/* Clients Table */}
      <div className="rounded-xl bg-[#111624] border border-slate-800 overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Client ID</th>
                <th className="py-3 px-4">Client Name</th>
                <th className="py-3 px-4">Risk Profile</th>
                <th className="py-3 px-4">KYC Status</th>
                <th className="py-3 px-4">Accounts</th>
                <th className="py-3 px-4">Target Risk</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-mono">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto text-indigo-400 mb-1" />
                    Loading client directory...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-mono">
                    No clients found matching filter.
                  </td>
                </tr>
              ) : (
                filtered.map((client) => (
                  <tr key={client.client_id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-indigo-400">
                      {client.client_id}
                    </td>
                    <td className="py-3 px-4 font-medium">{client.name}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                        {client.risk_profile}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                        <UserCheck className="w-3.5 h-3.5" />
                        {client.kyc_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono">{client.accounts_count} accounts</td>
                    <td className="py-3 px-4 text-slate-400">{client.target_risk}</td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleLaunchQuery(client.client_id)}
                        className="px-2.5 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/40 font-semibold text-[11px] inline-flex items-center gap-1 transition-all cursor-pointer"
                      >
                        <span>Query</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
