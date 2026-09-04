import React from "react";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className = "",
}) => {
  return (
    <div
      className={`p-8 rounded-lg bg-[#0c101a] border border-slate-800/80 text-center flex flex-col items-center justify-center space-y-3 ${className}`}
    >
      {Icon && (
        <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400">
          <Icon className="w-5 h-5" aria-hidden="true" />
        </div>
      )}
      <div className="space-y-1 max-w-md">
        <h4 className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider">
          {title}
        </h4>
        <p className="text-xs text-slate-400 leading-relaxed">
          {description}
        </p>
      </div>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-2 px-3 py-1.5 rounded bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 text-xs font-mono font-medium transition-colors cursor-pointer"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};
