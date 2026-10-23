import React from "react";
import { useOutletContext } from "react-router-dom";
import { Database, Bot, FileCode, Box, ShieldAlert } from "lucide-react";
import { DiagnosticCard } from "../components/ui/DiagnosticCard";
import { SystemStatusResponse, HealthResponse } from "../types/system";

interface ContextType {
  health: HealthResponse | null;
  systemStatus: SystemStatusResponse | null;
  isBackendConnected: boolean;
  isLoading: boolean;
  reload: () => void;
}

export const DashboardPage: React.FC = () => {
  const { systemStatus, isBackendConnected, isLoading } = useOutletContext<ContextType>();

  const dbDiagnostic = systemStatus?.components?.database;
  const aiDiagnostic = systemStatus?.components?.ai_runtime;
  const modelDiagnostic = systemStatus?.components?.model_artifacts;
  const sandboxDiagnostic = systemStatus?.components?.sandbox;

  return (
    <div className="space-y-8">
      {/* Platform Title Banner */}
      <div className="border border-[#1F2937] bg-gradient-to-r from-[#111827] via-[#111827] to-[#1E1B4B]/30 rounded-2xl p-6 md:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono mb-3">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              Phase 1: Project Foundation & Architecture
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
              PromptForge AI Console
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Research-oriented platform for verifiable prompt-to-software engineering,
              bidirectional requirement traceability, regression risk estimation, and isolated verification.
            </p>
          </div>

          <div className="flex flex-col items-start md:items-end gap-1.5 font-mono text-xs text-slate-400">
            <div>
              Platform Status:{" "}
              <span
                className={`font-semibold ${
                  systemStatus?.overall_status === "ready"
                    ? "text-emerald-400"
                    : systemStatus?.overall_status === "degraded"
                    ? "text-amber-400"
                    : "text-slate-300"
                }`}
              >
                {systemStatus?.overall_status ? systemStatus.overall_status.toUpperCase() : "CHECKING..."}
              </span>
            </div>
            <div>Architecture Mode: <span className="text-cyan-400">Local-First / Open-Weights</span></div>
            <div>Execution Sandbox: <span className="text-slate-400">Phase 4 Docker Isolation</span></div>
          </div>
        </div>
      </div>

      {/* Backend Disconnection Warning if offline */}
      {!isBackendConnected && !isLoading && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold block text-rose-200">Backend API Disconnected</span>
            FastAPI backend is unreachable on <code className="font-mono text-xs bg-rose-950/60 px-1 py-0.5 rounded">http://localhost:8000/api/v1</code>.
            Ensure the FastAPI server is running with <code className="font-mono text-xs bg-rose-950/60 px-1 py-0.5 rounded">uvicorn app.main:app --reload</code>.
          </div>
        </div>
      )}

      {/* Real Subsystem Diagnostic Grid */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-semibold text-slate-100">Subsystem Diagnostics & Resource Telemetry</h3>
            <p className="text-xs text-slate-400">
              Live validation of configured database, local AI runtime, filesystem model checkpoints, and execution sandbox.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <DiagnosticCard
            title="PostgreSQL 16"
            icon={<Database className="w-5 h-5 text-cyan-400" />}
            diagnostic={dbDiagnostic}
            isLoading={isLoading}
          />
          <DiagnosticCard
            title="Local AI Runtime (Ollama)"
            icon={<Bot className="w-5 h-5 text-violet-400" />}
            diagnostic={aiDiagnostic}
            isLoading={isLoading}
          />
          <DiagnosticCard
            title="Model Artifacts"
            icon={<FileCode className="w-5 h-5 text-amber-400" />}
            diagnostic={modelDiagnostic}
            isLoading={isLoading}
          />
          <DiagnosticCard
            title="Execution Sandbox"
            icon={<Box className="w-5 h-5 text-slate-400" />}
            diagnostic={sandboxDiagnostic}
            isLoading={isLoading}
          />
        </div>
      </section>

      {/* Architecture Pipeline Map */}
      <section className="bg-[#111827] border border-[#1F2937] rounded-xl p-6">
        <h3 className="text-base font-semibold text-white mb-2">Platform Verification Pipeline</h3>
        <p className="text-xs text-slate-400 mb-6">
          Unlike generic prompt chatbots, PromptForge AI enforces strict verification boundaries where model predictions are never conflated with deterministic test outcomes.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-cyan-400 font-semibold">01. Prompt Intelligence</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">Phase 2</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Accepts software requests, classifies task type, detects ambiguity, and flags missing constraints via trainable encoder.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-cyan-400 font-semibold">02. Requirement Traceability</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">Phase 3</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Extracts schema-validated functional/security requirements and generates bidirectional NetworkX graph linking requirements to code and tests.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-cyan-400 font-semibold">03. Code Gen & Isolated Sandbox</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">Phase 4</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Generates code through local open-weight model (Qwen2.5-Coder) and executes tests in isolated, non-networked Docker sandbox.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-cyan-400 font-semibold">04. Predictive Regression ML</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">Phase 5</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              LightGBM model trained on diff metadata and test history to score failure risk and prioritize regression suites.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-cyan-400 font-semibold">05. Evidence-Guided Repair</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">Phase 6</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Feeds failure trace, static analysis output, and requirement criteria back into code model with bounded repair budget.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-cyan-400 font-semibold">06. Experimentation & Evaluation</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">Phase 7</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Tracks MLflow runs, pass@k metrics, Semgrep security findings, and execution benchmarks with zero fabricated numbers.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};
