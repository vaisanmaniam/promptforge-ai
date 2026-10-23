import React from "react";
import { RefreshCw, Layers } from "lucide-react";
import { HealthResponse } from "../../types/system";

interface HeaderProps {
  health: HealthResponse | null;
  isBackendConnected: boolean;
  isLoading: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  isBackendConnected,
  isLoading,
  onRefresh,
}) => {
  return (
    <header className="h-16 border-b border-[#1F2937] bg-[#0B0F17]/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-violet-600 shadow-lg shadow-cyan-950/50">
          <Layers className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-base tracking-tight text-white">PromptForge AI</h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-violet-500/10 text-violet-400 border border-violet-500/20">
              Phase 1 Core
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">
            From Natural Language to Verified Software
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Backend Live Health Pill */}
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-[#111827] border border-[#1F2937] text-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              isBackendConnected
                ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]"
                : "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.7)]"
            }`}
          />
          <span className="font-medium text-slate-300">
            {isBackendConnected ? "Backend Online" : "Backend Offline"}
          </span>
          {health && (
            <span className="text-slate-500 font-mono text-[11px] hidden md:inline">
              v{health.version} [{health.environment}]
            </span>
          )}
        </div>

        {/* Refresh diagnostics button */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-2 rounded-lg bg-[#111827] border border-[#1F2937] text-slate-400 hover:text-white hover:border-[#374151] transition-all disabled:opacity-50"
          title="Refresh Diagnostics"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-cyan-400" : ""}`} />
        </button>
      </div>
    </header>
  );
};
