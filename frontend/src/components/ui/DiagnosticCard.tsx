import React, { useState } from "react";
import { ChevronDown, ChevronUp, Terminal, Info } from "lucide-react";
import { ComponentDiagnostic } from "../../types/system";
import { StatusBadge } from "./StatusBadge";

interface DiagnosticCardProps {
  title: string;
  icon: React.ReactNode;
  diagnostic?: ComponentDiagnostic;
  isLoading?: boolean;
}

export const DiagnosticCard: React.FC<DiagnosticCardProps> = ({
  title,
  icon,
  diagnostic,
  isLoading = false,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  if (isLoading) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#1E293B]" />
            <div className="h-5 w-24 bg-[#1E293B] rounded" />
          </div>
          <div className="h-6 w-20 bg-[#1E293B] rounded-full" />
        </div>
        <div className="h-4 w-3/4 bg-[#1E293B] rounded mb-2" />
        <div className="h-4 w-1/2 bg-[#1E293B] rounded" />
      </div>
    );
  }

  if (!diagnostic) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 text-slate-400">
        <div className="flex items-center gap-3 mb-2">
          {icon}
          <h3 className="font-semibold text-white">{title}</h3>
        </div>
        <p className="text-sm">Diagnostic telemetry unavailable.</p>
      </div>
    );
  }

  return (
    <div className="bg-[#111827] border border-[#1F2937] hover:border-[#374151] transition-colors rounded-xl p-5 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#1E293B] text-cyan-400 border border-[#334155]">
              {icon}
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 text-sm tracking-wide">{title}</h3>
              {diagnostic.latency_ms !== undefined && (
                <span className="text-xs text-slate-500 font-mono">
                  {diagnostic.latency_ms} ms
                </span>
              )}
            </div>
          </div>
          <StatusBadge status={diagnostic.status} size="sm" />
        </div>

        <p className="text-sm text-slate-300 leading-relaxed mb-3">
          {diagnostic.message}
        </p>

        {diagnostic.troubleshooting && (
          <div className="mt-3 p-3 rounded-lg bg-[#0B0F17] border border-amber-500/20 text-xs">
            <div className="flex items-center gap-1.5 text-amber-400 font-medium mb-1">
              <Terminal className="w-3.5 h-3.5" />
              <span>Recommended Action</span>
            </div>
            <code className="text-slate-300 font-mono block break-words select-all">
              {diagnostic.troubleshooting}
            </code>
          </div>
        )}
      </div>

      {diagnostic.details && Object.keys(diagnostic.details).length > 0 && (
        <div className="mt-4 pt-3 border-t border-[#1F2937]/80">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center justify-between w-full text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <span className="flex items-center gap-1">
              <Info className="w-3.5 h-3.5" />
              Inspection Details
            </span>
            {showDetails ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>

          {showDetails && (
            <pre className="mt-2 p-2.5 rounded bg-[#0B0F17] border border-[#1F2937] text-[11px] font-mono text-cyan-300/90 overflow-x-auto">
              {JSON.stringify(diagnostic.details, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};
