import React, { useEffect, useState } from "react";
import {
  LayoutDashboard,
  MessageSquareCode,
  Users,
  Network,
  Wrench,
  ShieldCheck,
  Activity,
  BarChart3,
  Layers,
  Cpu,
  RefreshCw,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import type { HealthResponse, ReadinessResponse } from "../api/types";

export type NavPage =
  | "dashboard"
  | "ask"
  | "clients"
  | "agents"
  | "tools"
  | "security"
  | "reliability"
  | "observability"
  | "architecture";

interface ShellProps {
  currentPage: NavPage;
  onSelectPage: (page: NavPage) => void;
  selectedClientId?: string;
  onSelectClient?: (clientId: string) => void;
  children: React.ReactNode;
}

export const Shell: React.FC<ShellProps> = ({
  currentPage,
  onSelectPage,
  children,
}) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [ready, setReady] = useState<ReadinessResponse | null>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState(false);

  const checkStatus = async () => {
    setIsLoadingHealth(true);
    try {
      const [h, r] = await Promise.all([
        arbiterApi.getHealth().catch(() => null),
        arbiterApi.getReadiness().catch(() => null),
      ]);
      setHealth(h);
      setReady(r);
    } finally {
      setIsLoadingHealth(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const timer = setInterval(checkStatus, 30000);
    return () => clearInterval(timer);
  }, []);

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, badge: null },
    { id: "ask", label: "Ask Arbiter", icon: MessageSquareCode, badge: "Live" },
    { id: "clients", label: "Clients Book", icon: Users, badge: ready?.clients_loaded ? `${ready.clients_loaded}` : null },
    { id: "agents", label: "Agent Network", icon: Network, badge: "6 Agents" },
    { id: "tools", label: "Tool Verification", icon: Wrench, badge: "24 Tools" },
    { id: "security", label: "Security & Trust", icon: ShieldCheck, badge: "Active" },
    { id: "reliability", label: "Reliability Engine", icon: Activity, badge: "Active" },
    { id: "observability", label: "Observability", icon: BarChart3, badge: null },
    { id: "architecture", label: "Architecture", icon: Layers, badge: null },
  ] as const;

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0d14] text-slate-100 antialiased font-sans">
      {/* Top Global Header Bar */}
      <header className="h-14 border-b border-slate-800/80 bg-[#0f1420]/90 backdrop-blur-md px-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/20 border border-indigo-400/30">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold tracking-wider text-white text-base">ARBITER</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                  v1.0 Operations
                </span>
              </div>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-2 pl-4 border-l border-slate-800 text-xs text-slate-400">
            <span>Multi-Agent Financial AI & Operations Platform</span>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-3 text-xs">
          {/* API Health */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900/90 border border-slate-800">
            <span
              className={`w-2 h-2 rounded-full ${
                health?.status === "ok" ? "bg-emerald-400 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className="text-slate-400 font-mono">API:</span>
            <span className={health?.status === "ok" ? "text-emerald-400 font-semibold" : "text-rose-400 font-semibold"}>
              {health?.status === "ok" ? "ONLINE" : "OFFLINE"}
            </span>
          </div>

          {/* Readiness & Dataset */}
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900/90 border border-slate-800">
            <span
              className={`w-2 h-2 rounded-full ${
                ready?.status === "ready" ? "bg-emerald-400" : "bg-amber-500"
              }`}
            />
            <span className="text-slate-400 font-mono">DATA:</span>
            <span className="text-slate-200 font-medium font-mono">
              {ready?.clients_loaded ?? 0} Clients / {ready?.instruments_loaded ?? 0} Tickers
            </span>
          </div>

          {/* Model Provider */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900/90 border border-slate-800 font-mono text-[11px]">
            <span className="text-slate-500">MODEL:</span>
            <span className="text-indigo-300 font-medium">{ready?.llm_model || "valura-fast"}</span>
          </div>

          <button
            onClick={checkStatus}
            title="Refresh status"
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingHealth ? "animate-spin" : ""}`} />
          </button>
        </div>
      </header>

      {/* Main Layout Container with Sidebar */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar Navigation */}
        <aside className="w-64 border-r border-slate-800/80 bg-[#0c101a] p-3 flex flex-col justify-between shrink-0">
          <div className="space-y-1">
            <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Workspace & Console
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectPage(item.id as NavPage)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm"
                      : "text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? "text-indigo-400" : "text-slate-500"}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        isActive
                          ? "bg-indigo-950 text-indigo-300 border border-indigo-800"
                          : "bg-slate-900 text-slate-500 border border-slate-800"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Sidebar Footer Details */}
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-[11px] space-y-1.5 font-mono text-slate-400">
            <div className="flex justify-between items-center text-slate-500 text-[10px] uppercase font-bold">
              <span>Security Guard</span>
              <span className="text-emerald-400">STRICT</span>
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              Client Scope: Context-Bound
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              Tool Verifier: 24 Checks
            </div>
          </div>
        </aside>

        {/* Main Content Viewport */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#0a0d14]">
          {children}
        </main>
      </div>
    </div>
  );
};
