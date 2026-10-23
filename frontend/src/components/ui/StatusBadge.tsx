import React from "react";
import { ComponentStatus } from "../../types/system";

interface StatusBadgeProps {
  status: ComponentStatus | string;
  size?: "sm" | "md";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = "md" }) => {
  const getBadgeStyle = () => {
    switch (status) {
      case "ready":
        return {
          bg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
          dot: "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]",
          label: "READY",
        };
      case "unavailable":
        return {
          bg: "bg-rose-500/10 border-rose-500/30 text-rose-400",
          dot: "bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.5)]",
          label: "UNAVAILABLE",
        };
      case "not_configured":
        return {
          bg: "bg-slate-500/10 border-slate-500/30 text-slate-400",
          dot: "bg-slate-400",
          label: "NOT CONFIGURED",
        };
      case "not_trained":
        return {
          bg: "bg-amber-500/10 border-amber-500/30 text-amber-400",
          dot: "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]",
          label: "NOT TRAINED (BASELINE)",
        };
      default:
        return {
          bg: "bg-cyan-500/10 border-cyan-500/30 text-cyan-400",
          dot: "bg-cyan-400",
          label: status.toUpperCase(),
        };
    }
  };

  const style = getBadgeStyle();
  const padding = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  return (
    <span
      data-testid="status-badge"
      className={`inline-flex items-center gap-1.5 font-medium border rounded-full font-mono ${padding} ${style.bg}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      <span>{style.label}</span>
    </span>
  );
};
