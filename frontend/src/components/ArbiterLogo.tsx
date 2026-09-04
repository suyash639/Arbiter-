import React from "react";

interface ArbiterLogoProps {
  size?: number;
  className?: string;
}

export const ArbiterLogo: React.FC<ArbiterLogoProps> = ({ size = 28, className = "" }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
      aria-label="Arbiter Logo"
      role="img"
    >
      <rect width="32" height="32" rx="7" fill="#0f1422" />
      <rect x="0.5" y="0.5" width="31" height="31" rx="6.5" stroke="#263045" strokeWidth="1" />
      {/* Geometric Arbiter "A" Routing Motif */}
      <path d="M16 5L6 26H10.5L13 20.5H19L21.5 26H26L16 5Z" fill="#6366f1" fillOpacity="0.18" />
      <path
        d="M16 6.5L8 24.5H11.5L13.5 19.5H18.5L20.5 24.5H24L16 6.5Z"
        stroke="#818cf8"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      {/* Central Coordination Bridge */}
      <line x1="12" y1="18" x2="20" y2="18" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" />
      {/* Central Verification & Routing Nodes */}
      <circle cx="16" cy="18" r="2" fill="#10b981" />
      <circle cx="16" cy="7.5" r="1.5" fill="#38bdf8" />
    </svg>
  );
};
