import React from "react";

export type SystemStatusType =
  | "ONLINE"
  | "OFFLINE"
  | "READY"
  | "UNAVAILABLE"
  | "SUCCESS"
  | "REFUSED"
  | "ABSTAINED"
  | "UPSTREAM ISSUE"
  | "ERROR"
  | "CONFIGURED"
  | "NOT REPORTED";

interface StatusIndicatorProps {
  status: SystemStatusType | string;
  size?: "sm" | "md";
  showLabel?: boolean;
  className?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  size = "sm",
  showLabel = true,
  className = "",
}) => {
  const normStatus = (status || "NOT REPORTED").toUpperCase() as SystemStatusType;

  // Semantic styles for each status
  let dotColor = "bg-slate-400";
  let textColor = "text-slate-400";
  let containerBg = "bg-slate-900 border-slate-800";

  switch (normStatus) {
    case "ONLINE":
    case "READY":
    case "SUCCESS":
      dotColor = "bg-emerald-400";
      textColor = "text-emerald-400";
      containerBg = "bg-emerald-950/40 border-emerald-800/60";
      break;
    case "CONFIGURED":
      dotColor = "bg-indigo-400";
      textColor = "text-indigo-300";
      containerBg = "bg-indigo-950/40 border-indigo-800/60";
      break;
    case "ABSTAINED":
      dotColor = "bg-amber-400";
      textColor = "text-amber-300";
      containerBg = "bg-amber-950/40 border-amber-800/60";
      break;
    case "UPSTREAM ISSUE":
      dotColor = "bg-amber-500 animate-pulse";
      textColor = "text-amber-400";
      containerBg = "bg-amber-950/50 border-amber-700/60";
      break;
    case "REFUSED":
      dotColor = "bg-rose-400";
      textColor = "text-rose-300";
      containerBg = "bg-rose-950/40 border-rose-800/60";
      break;
    case "OFFLINE":
    case "UNAVAILABLE":
    case "ERROR":
      dotColor = "bg-rose-500";
      textColor = "text-rose-400";
      containerBg = "bg-rose-950/60 border-rose-800/80";
      break;
    default:
      dotColor = "bg-slate-500";
      textColor = "text-slate-400";
      containerBg = "bg-slate-900 border-slate-800";
  }

  const dotSize = size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2";
  const textClass = size === "sm" ? "text-[10px]" : "text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border font-mono font-bold tracking-wider ${containerBg} ${textColor} ${textClass} ${className}`}
      role="status"
      aria-label={`Status: ${normStatus}`}
    >
      <span className={`${dotSize} rounded-full ${dotColor} shrink-0`} aria-hidden="true" />
      {showLabel && <span>{normStatus}</span>}
    </span>
  );
};
