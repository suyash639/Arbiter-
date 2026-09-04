import React, { useEffect, useState } from "react";
import { ShieldCheck, AlertTriangle, CheckCircle2 } from "lucide-react";
import { arbiterApi } from "../api/client";
import type { SecuritySummary } from "../api/types";

export const SecurityPage: React.FC = () => {
  const [sec, setSec] = useState<SecuritySummary | null>(null);

  useEffect(() => {
    arbiterApi.getSecuritySummary().then(setSec).catch(() => {});
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-indigo-400" />
          Security Architecture & Trust Boundaries
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Enterprise defense-in-depth security layer enforcing pre-flight validation, indirect injection quarantine, and automated PII redaction.
        </p>
      </div>

      {/* Trust Boundary Flow Visualization */}
      <div className="p-6 rounded-xl bg-[#111624] border border-slate-800">
        <div className="text-[10px] font-mono uppercase font-bold text-slate-500 tracking-wider mb-4">
          Data Trust Boundary Flow
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
          {/* Column 1: Untrusted */}
          <div className="p-4 rounded-lg bg-rose-950/30 border border-rose-800/60 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-rose-300 font-mono">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              UNTRUSTED SURFACE
            </div>
            <ul className="text-[11px] text-slate-400 space-y-1 font-mono list-disc list-inside">
              <li>User Prompts & Inputs</li>
              <li>LLM Unconstrained Output</li>
              <li>Retrieved Notes & Memos</li>
              <li>Market News Headlines</li>
              <li>Model-Generated Tool Arguments</li>
            </ul>
          </div>

          {/* Column 2: Security Boundary */}
          <div className="p-4 rounded-lg bg-indigo-950/60 border border-indigo-500/60 shadow-lg text-center space-y-2">
            <div className="text-xs font-extrabold text-indigo-300 font-mono">
              🛡️ SECURITY GATEWAY
            </div>
            <p className="text-[11px] text-slate-300">
              Regex Jailbreak Filters + XML Quarantine + Tool Scope Verification + PAN/Bank Redactor
            </p>
            <div className="text-[10px] font-mono text-emerald-400 font-bold">
              ● ACTIVE ENFORCEMENT
            </div>
          </div>

          {/* Column 3: Trusted */}
          <div className="p-4 rounded-lg bg-emerald-950/30 border border-emerald-800/60 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-300 font-mono">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              TRUSTED CORE
            </div>
            <ul className="text-[11px] text-slate-400 space-y-1 font-mono list-disc list-inside">
              <li>Authoritative Client Context</li>
              <li>Tool Registry & Authorizations</li>
              <li>Deterministic Accounting Engine</li>
              <li>Verified Schema Responses</li>
              <li>Masked Citations</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Security Controls Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sec?.controls.map((ctrl, i) => (
          <div key={i} className="p-4 rounded-xl bg-[#111624] border border-slate-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-white">{ctrl.name}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold">
                  ACTIVE
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">{ctrl.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
