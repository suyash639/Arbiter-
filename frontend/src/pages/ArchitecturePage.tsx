import React from "react";
import { Layers, ArrowDown, Cpu, ShieldCheck, Wrench, Activity, BarChart3 } from "lucide-react";

export const ArchitecturePage: React.FC = () => {
  const tiers = [
    {
      title: "1. Client & Operations Console",
      icon: Cpu,
      color: "border-indigo-500/60 bg-indigo-950/40 text-indigo-300",
      description: "React 19 + TypeScript + Vite operations interface. Zero client-side business calculations; submits structured requests with explicit client scopes.",
    },
    {
      title: "2. FastAPI Service Boundary",
      icon: Layers,
      color: "border-sky-500/60 bg-sky-950/40 text-sky-300",
      description: "Thin asynchronous transport layer. Enforces Pydantic QueryRequest schema validation, correlation X-Request-ID propagation, security headers, and threadpool delegation.",
    },
    {
      title: "3. Enterprise Security Layer",
      icon: ShieldCheck,
      color: "border-rose-500/60 bg-rose-950/40 text-rose-300",
      description: "Defense-in-depth security: regex jailbreak scanner, XML boundary quarantine for retrieved notes/news, deterministic client isolation, and automated Indian PAN/account masking.",
    },
    {
      title: "4. Arbiter Orchestrator",
      icon: Cpu,
      color: "border-purple-500/60 bg-purple-950/40 text-purple-300",
      description: "Multi-agent coordinator. Evaluates natural language queries, classifies intent via Router Agent with safety overrides, and delegates to domain specialists.",
    },
    {
      title: "5. Specialist Agent Network",
      icon: Layers,
      color: "border-amber-500/60 bg-amber-950/40 text-amber-300",
      description: "6 dedicated domain agents: Book QA (16 tools), KYC Profile (2 tools), Notes Desk (2 tools), Market Desk (4 tools), Compliance (0 tools - safety refusal).",
    },
    {
      title: "6. Tool Verification Subsystem",
      icon: Wrench,
      color: "border-emerald-500/60 bg-emerald-950/40 text-emerald-300",
      description: "Authoritative 24-tool registry. Validates agent authorization, Pydantic argument schemas, client scope isolation, and result contracts before model exposure.",
    },
    {
      title: "7. Reliability & Fault Tolerance Engine",
      icon: Activity,
      color: "border-cyan-500/60 bg-cyan-950/40 text-cyan-300",
      description: "Circuit breaker (5 failures / 30s recovery), exponential backoff with full jitter (1s base, 8s max, 3 attempts), non-blocking threadpool timeout, and safe abstention fallback.",
    },
    {
      title: "8. Observability & Telemetry Subsystem",
      icon: BarChart3,
      color: "border-indigo-500/60 bg-indigo-950/40 text-indigo-300",
      description: "End-to-end RequestTrace indexing, token and cost accounting, latency percentiles (P50/P95), and sanitized JSONL audit logging.",
    },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center justify-center gap-2">
          <Layers className="w-6 h-6 text-indigo-400" />
          Arbiter End-to-End System Architecture
        </h1>
        <p className="text-xs text-slate-400 max-w-xl mx-auto">
          Production-grade multi-tier architecture separating transport, security boundaries, multi-agent reasoning, deterministic tools, and reliability.
        </p>
      </div>

      <div className="space-y-3 pt-4">
        {tiers.map((tier, index) => {
          const Icon = tier.icon;
          return (
            <React.Fragment key={index}>
              <div className={`p-4 rounded-xl border shadow-md ${tier.color} transition-all`}>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-700/80 shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold tracking-wide text-white">{tier.title}</h3>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed">{tier.description}</p>
                  </div>
                </div>
              </div>
              {index < tiers.length - 1 && (
                <div className="flex justify-center my-1 text-slate-600">
                  <ArrowDown className="w-4 h-4" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
