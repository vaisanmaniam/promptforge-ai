import React, { useState } from "react";
import {
  BrainCircuit,
  Sparkles,
  Wand2,
  AlertTriangle,
  CheckCircle2,
  Copy,
  Check,
  RotateCcw,
  Gauge,
  HelpCircle,
  FileCode,
  Tag,
} from "lucide-react";
import { analyzePrompt, optimizePrompt } from "../api/prompt";
import {
  AnalyzePromptResponse,
  OptimizePromptResponse,
} from "../types/prompt";

const SAMPLE_PROMPTS = [
  {
    label: "LRU Cache (High Quality)",
    category: "code_generation",
    text: "Implement a thread-safe LRU cache in Python using a doubly linked list and a hash map. Include get(key) and put(key, value) operations with O(1) time complexity. Add a capacity parameter and raise KeyError when an item is not found.",
  },
  {
    label: "Auth API (Needs Improvement)",
    category: "api_development",
    text: "Create a fast and secure login endpoint in FastAPI with database storage.",
  },
  {
    label: "Vague Request (Low Quality)",
    category: null,
    text: "Fix my code, it crashed with an error and make it good and scalable, etc.",
  },
];

export const PromptIntelligencePage: React.FC = () => {
  const [promptInput, setPromptInput] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isOptimizing, setIsOptimizing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalyzePromptResponse | null>(null);
  const [optimizationResult, setOptimizationResult] = useState<OptimizePromptResponse | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const handleAnalyze = async () => {
    if (!promptInput.trim()) return;
    setIsAnalyzing(true);
    setErrorMessage(null);
    try {
      const res = await analyzePrompt({
        prompt: promptInput,
        task_category: selectedCategory || null,
      });
      setAnalysisResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to analyze prompt. Ensure backend is running.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleOptimize = async () => {
    if (!promptInput.trim()) return;
    setIsOptimizing(true);
    setErrorMessage(null);
    try {
      const res = await optimizePrompt({
        prompt: promptInput,
        task_category: selectedCategory || null,
      });
      setOptimizationResult(res);
      // Also update analysis result with original evaluation
      setAnalysisResult({
        task_classification: res.task_classification,
        components: {
          detected: [],
          missing: [],
          uncertain: [],
          findings: {},
        },
        ambiguity: {
          has_ambiguity: res.optimization.clarification_questions.length > 0,
          findings: [],
          ambiguity_count: res.optimization.clarification_questions.length,
        },
        quality: res.original_quality,
        token_count: res.token_analysis.original_tokens,
        token_counting_method: res.token_analysis.counting_method,
        tokenizer_identity: res.token_analysis.tokenizer_identity,
        is_exact_tokens: res.token_analysis.is_exact,
      });
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to optimize prompt. Ensure backend is running.");
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleCopyOptimized = () => {
    if (!optimizationResult) return;
    navigator.clipboard.writeText(optimizationResult.optimization.optimized_prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleApplyOptimizedToEditor = () => {
    if (!optimizationResult) return;
    setPromptInput(optimizationResult.optimization.optimized_prompt);
    setOptimizationResult(null);
    setAnalysisResult(null);
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
    if (score >= 50) return "text-amber-400 border-amber-500/30 bg-amber-500/10";
    return "text-rose-400 border-rose-500/30 bg-rose-500/10";
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="border border-[#1F2937] bg-gradient-to-r from-[#111827] via-[#111827] to-[#1E1B4B]/30 rounded-2xl p-6 md:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              Phase 2: Custom Prompt Intelligence Engine
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
              Prompt Analysis & Optimization Studio
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Transparent ML task classification, multi-label component detection,
              deterministic 6-dimension scoring, and assumption-revealing prompt optimization.
            </p>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold block text-rose-200">Analysis Error</span>
            {errorMessage}
          </div>
        </div>
      )}

      {/* Prompt Editor & Controls */}
      <section className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <label htmlFor="prompt-input" className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <FileCode className="w-4 h-4 text-cyan-400" />
            Software Development Request
          </label>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Sample Prompts:</span>
            <div className="flex flex-wrap gap-1.5">
              {SAMPLE_PROMPTS.map((sample, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setPromptInput(sample.text);
                    setSelectedCategory(sample.category || "");
                    setAnalysisResult(null);
                    setOptimizationResult(null);
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-[#0B0F17] hover:bg-[#1E293B] text-slate-300 border border-[#1F2937] transition-colors"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <textarea
          id="prompt-input"
          value={promptInput}
          onChange={(e) => setPromptInput(e.target.value)}
          rows={5}
          placeholder="Enter a software engineering prompt (e.g., 'Implement a thread-safe LRU cache in Python with O(1) operations and KeyError exception handling')..."
          className="w-full bg-[#0B0F17] border border-[#1F2937] focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/60 rounded-lg p-4 text-sm text-slate-200 placeholder-slate-600 font-mono transition-colors resize-y outline-none"
        />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Tag className="w-4 h-4 text-slate-400" />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-[#0B0F17] border border-[#1F2937] text-slate-300 text-xs rounded-lg px-3 py-2 outline-none focus:border-cyan-500"
              >
                <option value="">Auto-Detect Category (ML Classifier)</option>
                <option value="code_generation">Code Generation</option>
                <option value="debugging">Debugging</option>
                <option value="code_review">Code Review</option>
                <option value="api_development">API Development</option>
                <option value="sql_generation">SQL Generation</option>
                <option value="test_generation">Test Generation</option>
                <option value="documentation">Documentation</option>
                <option value="devops">DevOps</option>
              </select>
            </div>

            <span className="text-xs text-slate-500 font-mono">
              {promptInput.length} chars | {promptInput.trim() ? promptInput.trim().split(/\s+/).length : 0} words
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing || !promptInput.trim()}
              className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-medium text-xs flex items-center gap-2 transition-all shadow-lg shadow-cyan-950/40"
            >
              <BrainCircuit className={`w-4 h-4 ${isAnalyzing ? "animate-spin" : ""}`} />
              {isAnalyzing ? "Analyzing..." : "Analyze Prompt"}
            </button>

            <button
              onClick={handleOptimize}
              disabled={isOptimizing || !promptInput.trim()}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 text-white font-medium text-xs flex items-center gap-2 transition-all shadow-lg shadow-violet-950/40"
            >
              <Wand2 className={`w-4 h-4 ${isOptimizing ? "animate-spin" : ""}`} />
              {isOptimizing ? "Optimizing..." : "Optimize Prompt"}
            </button>
          </div>
        </div>
      </section>

      {/* Analysis Results */}
      {analysisResult && (
        <section className="space-y-6">
          {/* Top Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Classification Card */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
              <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold block mb-2">
                Task Classification
              </span>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg font-bold text-white capitalize">
                  {analysisResult.task_classification.predicted_category.replace("_", " ")}
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                  {(analysisResult.task_classification.confidence * 100).toFixed(1)}% conf
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Model: <span className="text-slate-300 font-mono">{analysisResult.task_classification.model_name}</span>{" "}
                ({analysisResult.task_classification.method})
              </p>
            </div>

            {/* Quality Score Card */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
              <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold block mb-2">
                Overall Quality Score
              </span>
              <div className="flex items-center gap-3 mb-2">
                <span className={`text-3xl font-extrabold font-mono px-3 py-1 rounded-xl border ${getScoreColor(analysisResult.quality.overall_score)}`}>
                  {analysisResult.quality.overall_score.toFixed(1)}
                </span>
                <div>
                  <span className="text-xs font-semibold text-slate-300 block">
                    {analysisResult.quality.overall_score >= 75
                      ? "Production Ready"
                      : analysisResult.quality.overall_score >= 50
                      ? "Actionable / Missing Constraints"
                      : "Critical Information Gaps"}
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Deterministic Scale (0-100)
                  </span>
                </div>
              </div>
              <p className="text-[11px] text-slate-500">
                Formula: {analysisResult.quality.scoring_version}
              </p>
            </div>

            {/* Token Analysis Card */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
              <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold block mb-2">
                Token Count & Efficiency
              </span>
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl font-bold font-mono text-cyan-400">
                  {analysisResult.token_count}
                </span>
                <span className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                  analysisResult.is_exact_tokens
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                }`}>
                  {analysisResult.is_exact_tokens ? "EXACT (BPE)" : "ESTIMATED"}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Tokenizer: <span className="text-slate-300 font-mono">{analysisResult.tokenizer_identity}</span>
              </p>
            </div>
          </div>

          {/* 6 Dimension Sub-scores Breakdown */}
          {analysisResult.quality.dimension_scores && (
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Gauge className="w-4 h-4 text-cyan-400" />
                Quality Dimension Breakdown (Deterministic Sub-scores)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(analysisResult.quality.dimension_scores).map(([key, dim]) => (
                  <div key={key} className="p-3.5 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="font-semibold text-slate-300 capitalize">{dim.dimension.replace("_", " ")}</span>
                      <span className="font-mono text-cyan-400 font-medium">
                        {dim.score} / 100 <span className="text-slate-500 text-[10px]">({(dim.weight * 100)}%)</span>
                      </span>
                    </div>
                    <div className="w-full bg-[#1F2937] rounded-full h-1.5 mb-2 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-cyan-500 to-violet-500 h-1.5 rounded-full"
                        style={{ width: `${dim.score}%` }}
                      />
                    </div>
                    <p className="text-[11px] text-slate-400 leading-tight">{dim.explanation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Component & Ambiguity Inspection */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Components Present vs Missing */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Software Engineering Components
              </h3>
              <div className="space-y-3">
                <div>
                  <span className="text-xs text-slate-400 block mb-1.5">Detected Components:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {analysisResult.components.detected.length > 0 ? (
                      analysisResult.components.detected.map((c) => (
                        <span key={c} className="px-2 py-0.5 rounded text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono">
                          ✓ {c.replace("_", " ")}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-slate-500 italic">None detected</span>
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-xs text-slate-400 block mb-1.5">Missing Components:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {analysisResult.components.missing.length > 0 ? (
                      analysisResult.components.missing.map((c) => (
                        <span key={c} className="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                          ✕ {c.replace("_", " ")}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-emerald-400">All core components present!</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Ambiguity & Clarifications */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-amber-400" />
                Ambiguity Detection & Clarifications
              </h3>

              {analysisResult.ambiguity.findings.length > 0 ? (
                <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
                  {analysisResult.ambiguity.findings.map((f, idx) => (
                    <div key={idx} className="p-2.5 rounded bg-[#0B0F17] border border-amber-500/20 text-xs">
                      <div className="flex items-center gap-1.5 text-amber-300 font-semibold mb-0.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        Ambiguous term: "{f.term}"
                      </div>
                      <p className="text-slate-400 text-[11px] mb-1">{f.explanation}</p>
                      <p className="text-cyan-300 text-[11px] italic font-mono">Clarify: {f.clarification_question}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400">
                  No subjective qualifiers or open-ended ambiguities detected. Phrasing is measurable.
                </p>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Optimization Results View */}
      {optimizationResult && (
        <section className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1F2937] pb-4">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-semibold text-violet-400 mb-1">
                <Wand2 className="w-4 h-4" />
                Prompt Optimization Complete
              </div>
              <h3 className="text-lg font-bold text-white">Before & After Optimization</h3>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleCopyOptimized}
                className="px-3 py-1.5 rounded-lg bg-[#0B0F17] hover:bg-[#1E293B] border border-[#1F2937] text-slate-200 text-xs flex items-center gap-1.5 transition-colors"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-cyan-400" />}
                {copied ? "Copied to Clipboard!" : "Copy Optimized Prompt"}
              </button>

              <button
                onClick={handleApplyOptimizedToEditor}
                className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs flex items-center gap-1.5 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Apply & Re-analyze
              </button>
            </div>
          </div>

          {/* Token & Quality Delta Card */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-xl bg-[#0B0F17] border border-[#1F2937]">
            <div>
              <span className="text-xs text-slate-500 block">Quality Improvement</span>
              <span className="text-lg font-bold font-mono text-emerald-400">
                {optimizationResult.original_quality.overall_score.toFixed(1)} → {optimizationResult.optimized_quality.overall_score.toFixed(1)}
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-500 block">Token Expansion</span>
              <span className="text-lg font-bold font-mono text-cyan-400">
                {optimizationResult.token_analysis.original_tokens} → {optimizationResult.token_analysis.optimized_tokens}
              </span>
              <span className="text-[11px] text-slate-500 ml-1">
                (+{optimizationResult.token_analysis.percentage_change}%)
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-500 block">Counting Method</span>
              <span className="text-xs font-mono text-slate-300">
                {optimizationResult.token_analysis.counting_method} ({optimizationResult.token_analysis.is_exact ? "Exact" : "Estimated"})
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-500 block">Sections Injected</span>
              <span className="text-lg font-bold font-mono text-violet-400">
                {optimizationResult.optimization.added_sections.length} sections
              </span>
            </div>
          </div>

          {/* Proposed Assumptions Requiring Confirmation */}
          {optimizationResult.optimization.assumptions.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
              <div className="flex items-center gap-2 text-amber-300 font-semibold text-xs mb-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                Proposed Assumptions Requiring Confirmation
              </div>
              <ul className="space-y-1 text-xs text-slate-300">
                {optimizationResult.optimization.assumptions.map((asm, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-amber-400 font-bold">•</span>
                    <span>{asm}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Prompt Comparison View */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">
                Original Request
              </span>
              <div className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937] text-xs text-slate-300 font-mono whitespace-pre-wrap min-h-[220px]">
                {optimizationResult.optimization.original_prompt}
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400 block">
                Optimized Structured Software Prompt
              </span>
              <div className="p-4 rounded-lg bg-[#0B0F17] border border-cyan-500/30 text-xs text-slate-200 font-mono whitespace-pre-wrap min-h-[220px] select-all">
                {optimizationResult.optimization.optimized_prompt}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
