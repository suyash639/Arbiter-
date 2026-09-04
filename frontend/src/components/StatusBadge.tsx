import React from "react";
import { CheckCircle2, AlertTriangle, ShieldAlert, XCircle } from "lucide-react";

interface StatusBadgeProps {
  abstained: boolean;
  refused: boolean;
  flags?: string[];
  hasError?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  abstained,
  refused,
  flags = [],
  hasError = false,
}) => {
  if (hasError) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">
        <XCircle className="w-3.5 h-3.5 text-rose-400" />
        ERROR
      </span>
    );
  }

  if (refused) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">
        <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
        POLICY REFUSED
      </span>
    );
  }

  if (abstained) {
    const isUpstream = flags.includes("upstream_issue");
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
        {isUpstream ? "UPSTREAM FALLBACK" : "ABSTAINED"}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
      SUCCESS
    </span>
  );
};
