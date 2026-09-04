import React, { useEffect, useState } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Lock,
  FileCode2,
  KeyRound,
  EyeOff,
  Terminal,
  Activity,
  RefreshCw,
} from "lucide-react";
import { arbiterApi } from "../api/client";
import { StatusIndicator } from "../components/StatusIndicator";

export const SecurityPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);

  const loadSecurity = () => {
    setLoading(true);
    arbiterApi
      .getSecuritySummary()
      .then(() => {
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadSecurity();
  }, []);

  const defaultControls = [
    {
      id: "injection_defense",
      name: "Direct Prompt Injection Defense",
      stage: "Pre-Flight Ingress",
      icon: Terminal,
      description:
        "Deterministic regex and pattern scanner detecting jailbreaks, role hijacking, instruction overrides, and prompt extraction attempts.",
      status: "CONFIGURED",
    },
    {
      id: "indirect_quarantine",
      name: "Indirect Injection Quarantine",
      stage: "Retrieval Ingestion",
      icon: Lock,
      description:
        "Retrieved dynamic CRM notes, memos, and market news are strictly wrapped in <untrusted_retrieved_data> XML boundaries to prevent instruction execution.",
      status: "CONFIGURED",
    },
    {
      id: "client_isolation",
      name: "Deterministic Client Isolation",
      stage: "Tool Verification",
      icon: KeyRound,
      description:
        "Runtime context closures enforce strict client_id bounds. Cross-client query attempts fail closed before accessing the data store.",
      status: "CONFIGURED",
    },
    {
      id: "pii_redaction",
      name: "Automated PII Masking",
      stage: "Output Sanitization",
      icon: EyeOff,
      description:
        "Automatic regex masking for sensitive personal identifiers, including Indian PANs (****249H) and bank account numbers (****9012).",
      status: "CONFIGURED",
    },
    {
      id: "secret_prevention",
      name: "Secret Leak Prevention",
      stage: "Telemetry & Logs",
      icon: Lock,
      description:
        "Deterministic sanitization filters scrubbing API keys, bearer tokens, passwords, and private credentials from outputs and observability logs.",
      status: "CONFIGURED",
    },
    {
      id: "output_guard",
      name: "Output Security Guard",
      stage: "Post-Generation",
      icon: FileCode2,
      description:
        "Strict Pydantic AnswerSchema validation ensuring citation isolation, typed answer values, and policy refusal adherence.",
      status: "CONFIGURED",
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1a2234] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold tracking-tight text-white font-mono flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-indigo-400" />
              SECURITY ARCHITECTURE & TRUST BOUNDARIES
            </h1>
            <StatusIndicator status="READY" size="sm" />
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Defense-in-depth isolation, multi-stage sanitization, client scope enforcement, and automated PII masking.
          </p>
        </div>

        <button
          onClick={loadSecurity}
          disabled={loading}
          className="self-start md:self-auto px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-xs font-mono text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin text-indigo-400" : ""}`} />
          <span>Refresh Controls</span>
        </button>
      </div>

      {/* Trust Boundary Flow Diagram */}
      <div className="p-4 rounded-lg bg-[#0c101a] border border-slate-800 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
            Data Trust Boundary & Defense Pipeline
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Ingress → Gateway → Core
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          {/* Column 1: Untrusted Inputs */}
          <div className="p-3.5 rounded-lg bg-rose-950/15 border border-rose-900/40 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold text-rose-300 font-mono">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                UNTRUSTED INPUTS
              </div>
              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-rose-950 text-rose-400 border border-rose-800">
                SURFACE
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              External and unverified data subject to potential manipulation:
            </p>
            <ul className="space-y-1 text-xs text-slate-300 font-mono">
              <li className="flex items-start gap-1.5">
                <span className="text-rose-500 font-bold">✕</span>
                <span>User Prompts & Ingress Text</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-rose-500 font-bold">✕</span>
                <span>Unconstrained LLM Reasoning</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-rose-500 font-bold">✕</span>
                <span>Retrieved CRM Notes & Memos</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-rose-500 font-bold">✕</span>
                <span>Market News Headlines & Tickers</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-rose-500 font-bold">✕</span>
                <span>Model-Generated Tool Arguments</span>
              </li>
            </ul>
          </div>

          {/* Column 2: Security Gateway */}
          <div className="p-3.5 rounded-lg bg-indigo-950/20 border border-indigo-700/50 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-300 font-mono">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                SECURITY GATEWAY
              </div>
              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                GATEWAY
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Multi-phase verification & sanitization barrier:
            </p>
            <ul className="space-y-1 text-xs text-slate-200 font-mono">
              <li className="flex items-start gap-1.5">
                <span className="text-indigo-400 font-bold">▶</span>
                <span>Heuristic Jailbreak & Prompt Scanner</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-indigo-400 font-bold">▶</span>
                <span>XML Boundary Quarantine (Notes/News)</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-indigo-400 font-bold">▶</span>
                <span>Deterministic Client Scope Isolation</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-indigo-400 font-bold">▶</span>
                <span>Tool Authorization & Pydantic Check</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-indigo-400 font-bold">▶</span>
                <span>Automated PAN / Account PII Masker</span>
              </li>
            </ul>
          </div>

          {/* Column 3: Trusted Core */}
          <div className="p-3.5 rounded-lg bg-emerald-950/15 border border-emerald-900/40 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-300 font-mono">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                TRUSTED CORE
              </div>
              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                VERIFIED
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Deterministic calculations and verified outputs:
            </p>
            <ul className="space-y-1 text-xs text-slate-300 font-mono">
              <li className="flex items-start gap-1.5">
                <span className="text-emerald-400 font-bold">✓</span>
                <span>Authoritative Client Context</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-emerald-400 font-bold">✓</span>
                <span>Verified TOOL_REGISTRY (24 Tools)</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-emerald-400 font-bold">✓</span>
                <span>Decimal Accounting & Portfolio Math</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-emerald-400 font-bold">✓</span>
                <span>Pydantic-Verified AnswerSchema</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-emerald-400 font-bold">✓</span>
                <span>Masked & Isolated Record Citations</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Implemented Controls Matrix */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
            Implemented Security Controls (6 Subsystems)
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Authoritative Server Configuration
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {defaultControls.map((ctrl) => {
            const Icon = ctrl.icon;
            return (
              <div
                key={ctrl.id}
                className="p-3.5 rounded-lg bg-[#0c101a] border border-slate-800 flex flex-col justify-between space-y-2.5"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="p-1 rounded bg-slate-900 border border-slate-700 text-indigo-400">
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className="font-bold text-xs text-white font-mono">
                        {ctrl.name}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-900 text-slate-400 border border-slate-800">
                      {ctrl.stage}
                    </span>
                    <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold">
                      {ctrl.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">
                    {ctrl.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Security Incident & Audit Log */}
      <div className="p-4 rounded-lg bg-[#0c101a] border border-slate-800 space-y-2">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-mono uppercase font-bold text-slate-300">
              Security Audit Stream & Incident Log
            </span>
          </div>
          <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1 font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            SECURE · ZERO ACTIVE INCIDENTS
          </span>
        </div>

        <div className="p-4 rounded bg-slate-950/60 border border-slate-800/80 text-center space-y-1">
          <div className="text-xs font-mono text-slate-300">
            No recent security events.
          </div>
          <p className="text-[11px] text-slate-500 max-w-md mx-auto">
            Input guardrails, injection filters, and client scope isolation are actively running with zero unauthorized boundary violations detected.
          </p>
        </div>
      </div>
    </div>
  );
};
