import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Play,
  Layers,
  Sparkles,
  GitBranch,
  ShieldAlert,
  Terminal,
  RefreshCw,
  Cpu,
} from "lucide-react";
import {
  analyzeChangeImpact,
  getModelStatus,
  selectTests,
  trainModel,
} from "../api/regression";
import {
  ingestProjectJson,
  triggerVerificationRun,
} from "../api/verification";
import {
  ChangeImpactReport,
  ModelStatusReport,
  PrioritizationStrategy,
  TestSelectionReport,
} from "../types/regression";
import { VerificationRun } from "../types/verification";

interface PresetScenario {
  id: string;
  name: string;
  changedFiles: string[];
  files: Record<string, string>;
}

const PRESET_CHANGES: PresetScenario[] = [
  {
    id: "calc-add",
    name: "Modify Calculator add()",
    changedFiles: ["calculator.py"],
    files: {
      "calculator.py": "def add(a, b):\n    # Implements REQ-001\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n",
      "tests/test_calculator.py": "from calculator import add, subtract\n\ndef test_add():\n    # Verifies REQ-001\n    assert add(2, 3) == 5\n\ndef test_subtract():\n    assert subtract(5, 3) == 2\n",
      "requirements.txt": "pytest>=8.0.0\n",
    },
  },
  {
    id: "lru-evict",
    name: "Drift in LRU Eviction",
    changedFiles: ["lru_cache.py"],
    files: {
      "lru_cache.py": "class LRUCache:\n    def __init__(self, capacity: int):\n        self.capacity = capacity\n        self.cache = {}\n    def get(self, key):\n        return self.cache.get(key, -1)\n    def put(self, key, value):\n        self.cache[key] = value\n",
      "tests/test_lru_cache.py": "from lru_cache import LRUCache\n\ndef test_cache_put_get():\n    c = LRUCache(2)\n    c.put(1, 10)\n    assert c.get(1) == 10\n",
      "requirements.txt": "pytest>=8.0.0\n",
    },
  },
  {
    id: "calc-test-only",
    name: "Direct Test File Change",
    changedFiles: ["tests/test_calculator.py"],
    files: {
      "calculator.py": "def add(a, b):\n    return a + b\n",
      "tests/test_calculator.py": "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
      "requirements.txt": "pytest>=8.0.0\n",
    },
  },
];

export const RegressionPage: React.FC = () => {
  const [projectId, setProjectId] = useState<string>("PROJ-001");
  const [changedFilesInput, setChangedFilesInput] = useState<string>("calculator.py");
  const [strategy, setStrategy] = useState<PrioritizationStrategy>("predictive");
  const [topK, setTopK] = useState<number | undefined>(undefined);
  const [budgetMs, setBudgetMs] = useState<number | undefined>(undefined);

  const [impactReport, setImpactReport] = useState<ChangeImpactReport | null>(null);
  const [selectionReport, setSelectionReport] = useState<TestSelectionReport | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatusReport | null>(null);

  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [isRunningTests, setIsRunningTests] = useState<boolean>(false);
  const [runResult, setRunResult] = useState<VerificationRun | null>(null);

  const [message, setMessage] = useState<{ text: string; type: "info" | "success" | "error" } | null>(null);

  useEffect(() => {
    loadModelStatus();
  }, []);

  const loadModelStatus = async () => {
    try {
      const status = await getModelStatus();
      setModelStatus(status);
    } catch (err: any) {
      console.warn("Could not load model status", err);
    }
  };

  const applyPresetChange = async (preset: typeof PRESET_CHANGES[0]) => {
    setChangedFilesInput(preset.changedFiles.join(", "));
    try {
      setIsAnalyzing(true);
      setMessage({ text: `Ingesting preset '${preset.name}'...`, type: "info" });
      const proj = await ingestProjectJson(preset.files, preset.name);
      setProjectId(proj.project_id);
      await runAnalysis(proj.project_id, preset.changedFiles);
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to load preset", type: "error" });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const runAnalysis = async (pId: string = projectId, files?: string[]) => {
    const fileList = files || changedFilesInput.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean);
    if (fileList.length === 0) {
      setMessage({ text: "Please provide at least one changed file path.", type: "error" });
      return;
    }

    setIsAnalyzing(true);
    setMessage(null);
    try {
      const impact = await analyzeChangeImpact(pId, fileList);
      setImpactReport(impact);

      // Immediately run selection under current strategy
      const sel = await selectTests(pId, fileList, strategy, topK, budgetMs);
      setSelectionReport(sel);
      setMessage({ text: `Impact analyzed: ${impact.changed_files.length} file(s), ${sel.selected_count} tests selected.`, type: "success" });
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || err.message, type: "error" });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleStrategyChange = async (newStrategy: PrioritizationStrategy) => {
    setStrategy(newStrategy);
    if (!impactReport) return;

    try {
      const fileList = changedFilesInput.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean);
      const sel = await selectTests(projectId, fileList, newStrategy, topK, budgetMs);
      setSelectionReport(sel);
    } catch (err: any) {
      setMessage({ text: err.message, type: "error" });
    }
  };

  const handleTrainSynthetic = async () => {
    setIsTraining(true);
    setMessage({ text: "Validating dataset and training pipeline with test samples...", type: "info" });
    try {
      const res = await trainModel(true, "RandomForestClassifier");
      if (res.success) {
        setMessage({ text: "Pipeline test model successfully trained and verified!", type: "success" });
        await loadModelStatus();
        if (impactReport) {
          await runAnalysis(projectId);
        }
      } else {
        setMessage({ text: res.message || "Training aborted", type: "error" });
      }
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || err.message, type: "error" });
    } finally {
      setIsTraining(false);
    }
  };

  const handleRunSelectedTests = async () => {
    if (!selectionReport || selectionReport.selected_tests.length === 0) {
      setMessage({ text: "No tests selected for execution.", type: "error" });
      return;
    }

    setIsRunningTests(true);
    setMessage({ text: "Executing selected tests in isolated Docker container...", type: "info" });
    try {
      // Build test command with exact test ids
      const testIds = selectionReport.selected_tests.map((t) => t.test_id);
      const command = ["pytest", "-v", ...testIds];
      const run = await triggerVerificationRun(projectId, undefined, command);
      setRunResult(run);
      setMessage({
        text: `Execution completed with status: ${run.status.toUpperCase()} (${run.passed_tests} passed, ${run.failed_tests} failed).`,
        type: run.status === "passed" ? "success" : "error",
      });
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || err.message, type: "error" });
    } finally {
      setIsRunningTests(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Predictive Regression Intelligence</h1>
              <p className="text-xs text-slate-400">
                Change-impact analysis, AST symbol tracking, and risk-weighted test prioritization.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {modelStatus?.is_trained ? (
              <span className="px-3 py-1 rounded-full text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5" />
                PREDICTIVE ML ACTIVE ({modelStatus.version})
              </span>
            ) : (
              <span className="px-3 py-1 rounded-full text-xs font-mono bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                DETERMINISTIC FALLBACK (MODEL UNTRAINED)
              </span>
            )}
          </div>
        </div>

        {/* Preset Change Quick Buttons */}
        <div className="mt-6 pt-4 border-t border-[#1F2937]/60">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
            Preset Change Scenarios:
          </span>
          <div className="flex flex-wrap gap-2">
            {PRESET_CHANGES.map((preset) => (
              <button
                key={preset.id}
                onClick={() => applyPresetChange(preset)}
                className="px-3 py-1.5 rounded-lg bg-[#0B0F17] hover:bg-cyan-950/40 border border-[#1F2937] hover:border-cyan-500/40 text-xs text-slate-300 hover:text-cyan-300 transition-colors flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                <span>{preset.name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications */}
      {message && (
        <div
          className={`p-4 rounded-xl border text-xs flex items-center gap-2 ${
            message.type === "success"
              ? "bg-emerald-950/30 border-emerald-500/40 text-emerald-300"
              : message.type === "error"
              ? "bg-red-950/30 border-red-500/40 text-red-300"
              : "bg-blue-950/30 border-blue-500/40 text-blue-300"
          }`}
        >
          {message.type === "success" && <CheckCircle className="w-4 h-4 shrink-0" />}
          {message.type === "error" && <AlertTriangle className="w-4 h-4 shrink-0" />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Controls Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Change Input & Strategy */}
        <div className="lg:col-span-1 border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            Change Specification
          </h2>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">Target Project ID</label>
            <input
              type="text"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="w-full px-3 py-2 bg-[#0B0F17] border border-[#1F2937] rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              placeholder="e.g. PROJ-001"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">
              Changed File Paths (comma / newline)
            </label>
            <textarea
              rows={3}
              value={changedFilesInput}
              onChange={(e) => setChangedFilesInput(e.target.value)}
              className="w-full px-3 py-2 bg-[#0B0F17] border border-[#1F2937] rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              placeholder="calculator.py&#10;tests/test_calculator.py"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1.5">Prioritization Strategy</label>
            <div className="grid grid-cols-3 gap-1.5 bg-[#0B0F17] p-1 rounded-lg border border-[#1F2937]">
              {(["predictive", "impact_based", "all_tests"] as PrioritizationStrategy[]).map((strat) => (
                <button
                  key={strat}
                  onClick={() => handleStrategyChange(strat)}
                  className={`py-1.5 px-2 rounded text-xs font-medium capitalize transition-all ${
                    strategy === strat
                      ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {strat.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Top-K Cutoff</label>
              <input
                type="number"
                min={1}
                value={topK || ""}
                onChange={(e) => setTopK(e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="All"
                className="w-full px-3 py-2 bg-[#0B0F17] border border-[#1F2937] rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Budget (ms)</label>
              <input
                type="number"
                min={10}
                step={50}
                value={budgetMs || ""}
                onChange={(e) => setBudgetMs(e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="No limit"
                className="w-full px-3 py-2 bg-[#0B0F17] border border-[#1F2937] rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <button
            onClick={() => runAnalysis()}
            disabled={isAnalyzing}
            className="w-full py-2.5 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            {isAnalyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Analyze & Prioritize Tests
          </button>
        </div>

        {/* Right: Change Impact Telemetry */}
        <div className="lg:col-span-2 border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              Structural Impact & Requirement Propagation
            </h2>
            {impactReport && (
              <span className="text-xs font-mono text-slate-400">{impactReport.analysis_id}</span>
            )}
          </div>

          {!impactReport ? (
            <div className="h-48 border border-dashed border-[#1F2937] rounded-lg flex flex-col items-center justify-center text-slate-500 text-xs">
              <span>Select a preset or click "Analyze & Prioritize Tests" to inspect change impact.</span>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Metric Pills */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                  <span className="text-slate-400 text-xs block">Changed Files</span>
                  <span className="text-lg font-bold text-white font-mono">
                    {impactReport.changed_files.length}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                  <span className="text-slate-400 text-xs block">Changed AST Symbols</span>
                  <span className="text-lg font-bold text-cyan-400 font-mono">
                    {impactReport.changed_symbols.length}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                  <span className="text-slate-400 text-xs block">Direct Requirements</span>
                  <span className="text-lg font-bold text-amber-400 font-mono">
                    {impactReport.directly_affected_requirements.length}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                  <span className="text-slate-400 text-xs block">Max Blast Depth</span>
                  <span className="text-lg font-bold text-purple-400 font-mono">
                    {impactReport.max_blast_radius_depth}
                  </span>
                </div>
              </div>

              {/* Directly & Downstream Requirements */}
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase text-slate-400 block">
                  Affected Requirements:
                </span>
                {impactReport.directly_affected_requirements.length === 0 &&
                impactReport.downstream_affected_requirements.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No requirement links affected by this change set.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {impactReport.directly_affected_requirements.map((req) => (
                      <div
                        key={req.requirement_id}
                        className="p-2.5 rounded-lg bg-amber-950/20 border border-amber-500/30 text-xs flex items-center justify-between"
                      >
                        <div>
                          <span className="font-mono font-bold text-amber-400 mr-2">{req.requirement_id}</span>
                          <span className="text-slate-200">{req.title}</span>
                        </div>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/20 text-amber-300">
                          {req.priority}
                        </span>
                      </div>
                    ))}
                    {impactReport.downstream_affected_requirements.map((req) => (
                      <div
                        key={req.requirement_id}
                        className="p-2.5 rounded-lg bg-purple-950/20 border border-purple-500/30 text-xs flex items-center justify-between"
                      >
                        <div>
                          <span className="font-mono font-bold text-purple-400 mr-2">{req.requirement_id}</span>
                          <span className="text-slate-200">{req.title}</span>
                        </div>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-purple-500/20 text-purple-300">
                          Blast Dependent
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Evidence Disclosures */}
              {impactReport.evidence_disclosures.length > 0 && (
                <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937] text-xs text-slate-400 space-y-1">
                  <span className="font-semibold text-slate-300 block">Evidence Disclosures:</span>
                  {impactReport.evidence_disclosures.map((d, i) => (
                    <li key={i} className="list-disc ml-4 text-[11px] text-slate-400">
                      {d}
                    </li>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Ranked & Selected Tests Table */}
      {selectionReport && (
        <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-cyan-400" />
                Ranked Regression Test Suite
              </h2>
              <p className="text-xs text-slate-400">
                Selected {selectionReport.selected_count} of {selectionReport.total_tests} tests{" "}
                (Est. {selectionReport.estimated_duration_ms}ms) under{" "}
                <span className="font-semibold text-cyan-400 capitalize">{selectionReport.strategy.replace("_", " ")}</span> strategy.
              </p>
            </div>

            <button
              onClick={handleRunSelectedTests}
              disabled={isRunningTests || selectionReport.selected_count === 0}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {isRunningTests ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Run Selected ({selectionReport.selected_count}) in Docker Sandbox
            </button>
          </div>

          {/* Fallback Notice */}
          {selectionReport.fallback_to_baseline && (
            <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-500/30 text-xs text-amber-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>
                <strong>Truthful Telemetry Notice:</strong> {selectionReport.fallback_reason}
              </span>
            </div>
          )}

          {/* Selected Tests Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border border-[#1F2937] rounded-lg overflow-hidden">
              <thead className="bg-[#0B0F17] text-slate-400 font-mono text-[11px] border-b border-[#1F2937]">
                <tr>
                  <th className="p-3 w-16">Rank</th>
                  <th className="p-3">Test Identifier</th>
                  <th className="p-3 w-28">Risk Score</th>
                  <th className="p-3 w-36">Method</th>
                  <th className="p-3">Ranking Explanations & Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F2937] text-slate-300">
                {selectionReport.selected_tests.map((test) => (
                  <tr key={test.test_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="p-3 font-mono font-bold text-cyan-400">#{test.rank}</td>
                    <td className="p-3">
                      <span className="font-mono text-white block">{test.test_id}</span>
                      <span className="text-[10px] text-slate-500">{test.file_path}</span>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-white">
                          {(test.score * 100).toFixed(1)}%
                        </span>
                        <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              test.score >= 0.7
                                ? "bg-red-500"
                                : test.score >= 0.4
                                ? "bg-amber-500"
                                : "bg-emerald-500"
                            }`}
                            style={{ width: `${test.score * 100}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#0B0F17] border border-[#1F2937] text-slate-300">
                        {test.method}
                      </span>
                    </td>
                    <td className="p-3 space-y-1">
                      {test.explanations.map((exp, idx) => (
                        <div key={idx} className="flex items-center gap-1.5 text-[11px] text-slate-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0" />
                          <span>{exp}</span>
                        </div>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Excluded Tests Panel */}
          {selectionReport.excluded_tests.length > 0 && (
            <div className="pt-4 border-t border-[#1F2937]">
              <h3 className="text-xs font-semibold uppercase text-slate-400 mb-2">
                Excluded Tests ({selectionReport.excluded_count}):
              </h3>
              <div className="space-y-2">
                {selectionReport.excluded_tests.map((ex) => (
                  <div
                    key={ex.test_id}
                    className="p-2.5 rounded-lg bg-[#0B0F17] border border-[#1F2937] text-xs flex items-center justify-between"
                  >
                    <div>
                      <span className="font-mono text-slate-300 mr-3">{ex.test_id}</span>
                      <span className="text-slate-500 text-[11px]">{ex.exclusion_reason}</span>
                    </div>
                    <span className="font-mono text-slate-500 text-xs">Rank #{ex.rank}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Execution Terminal Output (if run executed) */}
      {runResult && (
        <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              Docker Execution Console Logs ({runResult.id})
            </h2>
            <span
              className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold uppercase ${
                runResult.status === "passed"
                  ? "bg-emerald-500/20 text-emerald-300"
                  : "bg-red-500/20 text-red-300"
              }`}
            >
              {runResult.status}
            </span>
          </div>

          <pre className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937] text-xs font-mono text-slate-300 overflow-x-auto max-h-64 whitespace-pre-wrap">
            {runResult.stdout || runResult.stderr || "No console output recorded."}
          </pre>
        </div>
      )}

      {/* Model Lab & Training Pipeline Telemetry */}
      <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-cyan-400" />
            <h2 className="text-sm font-semibold text-white">Model Lifecycle & Training Lab</h2>
          </div>
          <button
            onClick={handleTrainSynthetic}
            disabled={isTraining}
            className="px-3 py-1.5 rounded-lg bg-cyan-950/40 hover:bg-cyan-900/60 border border-cyan-500/40 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            {isTraining ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            Train Pipeline (Synthetic Test)
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
            <span className="text-slate-400 block mb-1">Model State</span>
            <span className="font-mono font-bold text-white capitalize">
              {modelStatus?.status || "Unknown"}
            </span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
            <span className="text-slate-400 block mb-1">Features Expected</span>
            <span className="font-mono font-bold text-cyan-400">10 Numerical Features</span>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
            <span className="text-slate-400 block mb-1">Training Samples</span>
            <span className="font-mono font-bold text-emerald-400">
              {modelStatus?.training_sample_count || 0} observations
            </span>
          </div>
        </div>

        <p className="text-[11px] text-slate-400 leading-relaxed">
          <strong>Integrity & Provenance Policy:</strong> PromptForge AI enforces strict provenance tracking. Synthetic samples are labeled exclusively as <code className="text-cyan-300">synthetic_pipeline_test</code> and are never presented as real-world predictive evaluation metrics.
        </p>
      </div>
    </div>
  );
};
