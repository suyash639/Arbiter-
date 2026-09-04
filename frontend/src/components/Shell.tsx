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
  RefreshCw,
  Menu,
  X,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import type { HealthResponse, ReadinessResponse } from "../api/types";
import { ArbiterLogo } from "./ArbiterLogo";
import { StatusIndicator } from "./StatusIndicator";

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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

  const navSections = [
    {
      title: "WORKSPACE",
      items: [
        { id: "dashboard" as NavPage, label: "Console Overview", icon: LayoutDashboard },
        { id: "ask" as NavPage, label: "Ask Arbiter", icon: MessageSquareCode },
        { id: "clients" as NavPage, label: "Client Book", icon: Users },
      ],
    },
    {
      title: "SYSTEM",
      items: [
        { id: "agents" as NavPage, label: "Agent Network", icon: Network },
        { id: "tools" as NavPage, label: "Tool Verification", icon: Wrench },
        { id: "security" as NavPage, label: "Security & Trust", icon: ShieldCheck },
        { id: "reliability" as NavPage, label: "Reliability Engine", icon: Activity },
        { id: "observability" as NavPage, label: "Observability", icon: BarChart3 },
      ],
    },
    {
      title: "REFERENCE",
      items: [
        { id: "architecture" as NavPage, label: "Architecture", icon: Layers },
      ],
    },
  ];

  const handleNavClick = (pageId: NavPage) => {
    onSelectPage(pageId);
    setMobileMenuOpen(false);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#080c14] text-slate-100 antialiased font-sans">
      {/* Top Global Header Bar */}
      <header className="h-12 border-b border-[#1a2234] bg-[#0c101a] px-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1 rounded md:hidden text-slate-400 hover:text-white transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          {/* Brand Logo & Title */}
          <div className="flex items-center gap-2.5">
            <ArbiterLogo size={26} />
            <div className="flex items-baseline gap-2">
              <span className="font-extrabold tracking-wider text-white text-sm font-mono">
                ARBITER
              </span>
              <span className="text-[11px] text-slate-400 font-medium hidden sm:inline border-l border-slate-700 pl-2">
                Operations Console
              </span>
            </div>
          </div>
        </div>

        {/* Live Header Status Strip */}
        <div className="flex items-center gap-2.5 text-xs">
          {/* API Health */}
          <StatusIndicator
            status={health?.status === "ok" ? "ONLINE" : "OFFLINE"}
            size="sm"
          />

          {/* Dataset Status */}
          <div className="hidden md:flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 font-mono text-[10px] text-slate-300">
            <span className="text-slate-500 font-bold">DATA:</span>
            <span>{ready?.clients_loaded ?? 25} Clients / {ready?.instruments_loaded ?? 14} Tickers</span>
          </div>

          {/* LLM Model */}
          <div className="hidden lg:flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 font-mono text-[10px] text-indigo-300">
            <span className="text-slate-500 font-bold">LLM:</span>
            <span>{ready?.llm_model || "gemini-3.6-flash"}</span>
          </div>

          {/* Status Refresh */}
          <button
            onClick={checkStatus}
            title="Refresh system status"
            className="p-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
            aria-label="Refresh status"
          >
            <RefreshCw className={`w-3 h-3 ${isLoadingHealth ? "animate-spin text-indigo-400" : ""}`} />
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar Navigation */}
        <aside
          className={`fixed md:static inset-y-12 left-0 z-40 w-56 border-r border-[#1a2234] bg-[#0c101a] p-3 flex flex-col justify-between shrink-0 transform transition-transform duration-200 ease-in-out md:translate-x-0 ${
            mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <nav className="space-y-4">
            {navSections.map((sec, secIdx) => (
              <div key={secIdx} className="space-y-0.5">
                <div className="px-2 py-1 text-[9px] font-bold uppercase tracking-wider text-slate-500 font-mono">
                  {sec.title}
                </div>
                {sec.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = currentPage === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleNavClick(item.id)}
                      className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded text-xs transition-colors cursor-pointer text-left font-sans ${
                        isActive
                          ? "bg-indigo-600/15 text-indigo-300 font-semibold border-l-2 border-indigo-500"
                          : "text-slate-400 hover:bg-slate-900/80 hover:text-slate-200"
                      }`}
                    >
                      <Icon className={`w-3.5 h-3.5 ${isActive ? "text-indigo-400" : "text-slate-500"}`} />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            ))}
          </nav>

          {/* Sidebar Footer System Scope Summary */}
          <div className="p-2 rounded bg-slate-950/70 border border-slate-800/80 text-[10px] font-mono text-slate-400 space-y-0.5">
            <div className="flex justify-between items-center text-[9px] uppercase font-bold text-slate-500">
              <span>Security Isolation</span>
              <span className="text-emerald-400 font-bold">ENFORCED</span>
            </div>
            <div className="text-[10px] text-slate-400">
              Tool Verification: 24 Tools
            </div>
            <div className="text-[10px] text-slate-400">
              Financial Math: 100% Decimal
            </div>
          </div>
        </aside>

        {/* Mobile backdrop */}
        {mobileMenuOpen && (
          <div
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 bg-black/60 z-30 md:hidden"
            aria-hidden="true"
          />
        )}

        {/* Main Content Viewport */}
        <main className="flex-1 overflow-y-auto p-5 md:p-6 bg-[#080c14]">
          {children}
        </main>
      </div>
    </div>
  );
};
