import React from "react";
import { FlaskConical, Clock, CheckCircle } from "lucide-react";

export const ModelLabPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <FlaskConical className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Model Lab & Experiment Tracking</h2>
              <p className="text-xs text-slate-400">
                Model training pipelines, MLflow experiment tracking, evaluation benchmarks, and artifact registry.
              </p>
            </div>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-mono bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            PLANNED: PHASE 6
          </span>
        </div>

        <div className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937] text-xs text-slate-400 leading-relaxed mb-6">
          <span className="font-semibold text-slate-200 block mb-1">Implementation Note</span>
          This module is scheduled for implementation in <strong>Phase 6</strong>. It connects to the <code className="font-mono text-cyan-400">ai/</code> subsystem to manage dataset splits, run fine-tuning jobs (PEFT/LoRA), log metrics to MLflow, and benchmark local open-weight models against deterministic test suites.
        </div>

        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Phase 6 Planned Capabilities</h3>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-400">
            <li className="flex items-start gap-2 p-3 rounded-lg bg-[#0B0F17]/60 border border-[#1F2937]">
              <CheckCircle className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <span>Dataset split validation (train/val/test) with hash verification.</span>
            </li>
            <li className="flex items-start gap-2 p-3 rounded-lg bg-[#0B0F17]/60 border border-[#1F2937]">
              <CheckCircle className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <span>MLflow tracking for prompt classifier and regression model training runs.</span>
            </li>
            <li className="flex items-start gap-2 p-3 rounded-lg bg-[#0B0F17]/60 border border-[#1F2937]">
              <CheckCircle className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <span>Real metric evaluations (F1-score, accuracy, APFD for regression prioritization).</span>
            </li>
            <li className="flex items-start gap-2 p-3 rounded-lg bg-[#0B0F17]/60 border border-[#1F2937]">
              <CheckCircle className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <span>Provider-independent local model registry (Ollama/GGUF/Hugging Face checkpoints).</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
