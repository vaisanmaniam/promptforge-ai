import React, { useState, useEffect, useMemo } from "react";
import {
  GitFork,
  Sparkles,
  Layers,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
  Search,
  Zap,
  ArrowRight,
  ShieldCheck,
  RotateCcw,
  Network,
  Download,
  ListChecks,
} from "lucide-react";
import {
  extractRequirements,
  createSpecification,
  listSpecifications,
  getSpecification,
  getTraceabilityGraph,
  getImpactAnalysis,
} from "../api/requirement";
import {
  RequirementItem,
  RequirementSpecification,
  SpecificationSummary,
  TraceabilityGraph,
  TraceabilityNode,
  ValidationReport,
  CoverageReport,
  ImpactAnalysisReport,
} from "../types/requirement";

const PRESET_PROMPTS = [
  {
    name: "FastAPI REST API with Redis & JWT",
    category: "api_development",
    prompt:
      "Build a rate-limited REST API in FastAPI using Python 3.11 with Redis caching, JWT authentication, and O(1) cache lookups. Include strict Pydantic payload validation and error responses.",
  },
  {
    name: "Thread-Safe LRU Cache in Python",
    category: "code_generation",
    prompt:
      "Implement a thread-safe LRU cache in Python 3.11 with O(1) get and put time complexity, maximum capacity limit, TTL expiration, and unit tests covering concurrency.",
  },
  {
    name: "PostgreSQL Analytics Aggregator",
    category: "sql_generation",
    prompt:
      "Create a PostgreSQL 16 schema and query suite for real-time customer analytics. Support daily partition tables, composite indexing, and sub-second window aggregations.",
  },
  {
    name: "Ambiguous Microservice (With Gaps)",
    category: "code_generation",
    prompt:
      "Write a fast scalable backend service with a modern database that handles user data securely etc.",
  },
];

export const RequirementsPage: React.FC = () => {
  const [prompt, setPrompt] = useState<string>(PRESET_PROMPTS[0].prompt);
  const [taskCategory, setTaskCategory] = useState<string>(PRESET_PROMPTS[0].category);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Specification State
  const [spec, setSpec] = useState<RequirementSpecification | null>(null);
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [coverage, setCoverage] = useState<CoverageReport | null>(null);
  const [graph, setGraph] = useState<TraceabilityGraph | null>(null);
  const [specList, setSpecList] = useState<SpecificationSummary[]>([]);
  const [selectedSpecId, setSelectedSpecId] = useState<string>("");

  // UI Navigation & Filters
  const [activeTab, setActiveTab] = useState<"requirements" | "graph" | "validation" | "matrix">("requirements");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Graph & Impact State
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [impactReport, setImpactReport] = useState<ImpactAnalysisReport | null>(null);
  const [loadingImpact, setLoadingImpact] = useState<boolean>(false);

  // Load existing specifications list on mount
  useEffect(() => {
    loadSavedSpecs();
  }, []);

  const loadSavedSpecs = async () => {
    try {
      const res = await listSpecifications();
      setSpecList(res.specifications);
    } catch {
      // Non-fatal if offline
    }
  };

  const handleExtract = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setSelectedNodeId(null);
    setImpactReport(null);

    try {
      const res = await extractRequirements(prompt, taskCategory);
      setSpec(res.specification);
      setValidation(res.validation);
      setCoverage(res.coverage);

      // Also generate graph
      try {
        const graphRes = await getTraceabilityGraph(res.specification.id);
        setGraph(graphRes);
      } catch {
        // Fallback local graph building if spec not yet persisted
        buildLocalGraph(res.specification);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to extract requirements.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSpecification = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const saved = await createSpecification(prompt, undefined, taskCategory);
      setSpec(saved);
      setSelectedSpecId(saved.id);
      await loadSavedSpecs();

      // Refresh graph and coverage
      const [gRes, covRes] = await Promise.all([
        getTraceabilityGraph(saved.id),
        // coverage already extracted or fetch
        extractRequirements(prompt, taskCategory),
      ]);
      setGraph(gRes);
      setValidation(covRes.validation);
      setCoverage(covRes.coverage);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save specification.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSavedSpec = async (specId: string) => {
    if (!specId) return;
    setSelectedSpecId(specId);
    setLoading(true);
    setError(null);
    setSelectedNodeId(null);
    setImpactReport(null);

    try {
      const loaded = await getSpecification(specId);
      setSpec(loaded);
      setPrompt(loaded.source_prompt);
      if (loaded.task_category) setTaskCategory(loaded.task_category);

      const [gRes, extRes] = await Promise.all([
        getTraceabilityGraph(specId),
        extractRequirements(loaded.source_prompt, loaded.task_category),
      ]);
      setGraph(gRes);
      setValidation(extRes.validation);
      setCoverage(extRes.coverage);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load specification.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const buildLocalGraph = (currentSpec: RequirementSpecification) => {
    const nodes: TraceabilityNode[] = [
      {
        id: "PROMPT-ROOT",
        type: "prompt",
        label: "Source Prompt",
        category: "prompt",
        status: "source",
      },
    ];

    const edges = [];
    for (const req of currentSpec.requirements) {
      nodes.push({
        id: req.id,
        type: "requirement",
        label: `${req.id}: ${req.title}`,
        category: req.category,
        status: req.status,
        priority: req.priority,
      });

      edges.push({
        source: "PROMPT-ROOT",
        target: req.id,
        relation: "generates",
      });

      for (const dep of req.depends_on) {
        edges.push({
          source: req.id,
          target: dep,
          relation: "depends_on",
        });
      }
    }

    setGraph({
      nodes,
      edges,
      has_cycles: false,
      cycle_paths: [],
      isolated_nodes: [],
    });
  };

  const handleSelectNode = async (nodeId: string) => {
    setSelectedNodeId(nodeId);
    if (!spec || nodeId === "PROMPT-ROOT") {
      setImpactReport(null);
      return;
    }

    setLoadingImpact(true);
    try {
      const rep = await getImpactAnalysis(spec.id, nodeId);
      setImpactReport(rep);
    } catch {
      // Local impact computation fallback
      const downstream = spec.requirements
        .filter((r) => r.depends_on.includes(nodeId))
        .map((r) => r.id);
      const targetReq = spec.requirements.find((r) => r.id === nodeId);
      setImpactReport({
        target_req_id: nodeId,
        upstream_dependencies: targetReq ? targetReq.depends_on : [],
        downstream_dependents: downstream,
        impact_depth: downstream.length > 0 ? 1 : 0,
        risk_level: downstream.length > 2 ? "high" : downstream.length > 0 ? "medium" : "low",
      });
    } finally {
      setLoadingImpact(false);
    }
  };

  // Filtered requirements
  const filteredRequirements = useMemo(() => {
    if (!spec) return [];
    return spec.requirements.filter((r) => {
      const matchesCat = categoryFilter === "all" || r.category === categoryFilter;
      const matchesQuery =
        searchQuery === "" ||
        r.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCat && matchesQuery;
    });
  }, [spec, categoryFilter, searchQuery]);

  // Export specification as JSON
  const handleExportJSON = () => {
    if (!spec) return;
    const blob = new Blob([JSON.stringify(spec, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${spec.id}_specification.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <GitFork className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-white">Requirement Intelligence & Traceability Engine</h2>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  Phase 3 Active
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic requirement extraction, explicit vs. inferred categorization, NetworkX directed graphs, and blast-radius analysis.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {specList.length > 0 && (
              <select
                aria-label="Load Saved Specification"
                value={selectedSpecId}
                onChange={(e) => handleSelectSavedSpec(e.target.value)}
                className="bg-[#0B0F17] border border-[#1F2937] text-xs text-slate-300 rounded-lg px-3 py-1.5 focus:border-cyan-500 focus:outline-none"
              >
                <option value="">-- Load Saved Spec ({specList.length}) --</option>
                {specList.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title} ({s.total_requirements} reqs)
                  </option>
                ))}
              </select>
            )}
            {spec && (
              <button
                onClick={handleExportJSON}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#1F2937] text-slate-300 hover:text-white hover:bg-[#374151] transition"
              >
                <Download className="w-3.5 h-3.5" />
                Export JSON
              </button>
            )}
          </div>
        </div>

        {/* Preset Selector */}
        <div className="flex items-center gap-2 flex-wrap text-xs pt-2 border-t border-[#1F2937]/60">
          <span className="text-slate-400 flex items-center gap-1">
            <Zap className="w-3.5 h-3.5 text-amber-400" /> Presets:
          </span>
          {PRESET_PROMPTS.map((preset, idx) => (
            <button
              key={idx}
              onClick={() => {
                setPrompt(preset.prompt);
                setTaskCategory(preset.category);
              }}
              className="px-2.5 py-1 rounded bg-[#0B0F17] hover:bg-[#1E293B] border border-[#1F2937] text-slate-300 text-[11px] transition"
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Input & Control Panel */}
      <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Source Software Prompt
            </label>
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-slate-400">{prompt.length} chars</span>
              <select
                aria-label="Category Override"
                value={taskCategory}
                onChange={(e) => setTaskCategory(e.target.value)}
                className="bg-[#0B0F17] border border-[#1F2937] text-xs text-slate-300 rounded px-2.5 py-1 focus:border-cyan-500 focus:outline-none"
              >
                <option value="code_generation">Code Generation</option>
                <option value="api_development">API Development</option>
                <option value="sql_generation">SQL Generation</option>
                <option value="debugging">Debugging</option>
                <option value="test_generation">Test Generation</option>
                <option value="devops">DevOps</option>
              </select>
            </div>
          </div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            placeholder="Describe the software component, API endpoint, or algorithm to extract requirements from..."
            className="w-full bg-[#0B0F17] border border-[#1F2937] rounded-lg p-3 text-xs text-slate-200 placeholder-slate-500 font-mono focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition"
          />
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={handleExtract}
            disabled={loading || !prompt.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-sm shadow-cyan-500/20"
          >
            {loading ? (
              <>
                <RotateCcw className="w-4 h-4 animate-spin" />
                Extracting...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Extract Requirements
              </>
            )}
          </button>

          <button
            onClick={handleSaveSpecification}
            disabled={loading || !prompt.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium bg-[#1F2937] hover:bg-[#374151] text-white transition disabled:opacity-50"
          >
            <ListChecks className="w-4 h-4 text-emerald-400" />
            Save Specification
          </button>
        </div>
      </div>

      {/* Specification Metrics Summary Bar */}
      {spec && coverage && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-[#111827] border border-[#1F2937]">
            <span className="text-[11px] font-semibold uppercase text-slate-400 block mb-1">
              Total Requirements
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-cyan-400">
                {coverage.total_requirements}
              </span>
              <span className="text-xs text-slate-400">items</span>
            </div>
            <div className="mt-2 text-[10px] text-slate-400 flex items-center gap-2">
              <span className="text-emerald-400">{coverage.explicit_count} explicit</span>
              <span>•</span>
              <span className="text-purple-400">{coverage.inferred_count} inferred</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#111827] border border-[#1F2937]">
            <span className="text-[11px] font-semibold uppercase text-slate-400 block mb-1">
              AC Coverage
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-emerald-400">
                {coverage.acceptance_criteria_coverage_pct}%
              </span>
              <span className="text-xs text-slate-400">testable</span>
            </div>
            <p className="mt-2 text-[10px] text-slate-400">
              Requirements with defined acceptance tests
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#111827] border border-[#1F2937]">
            <span className="text-[11px] font-semibold uppercase text-slate-400 block mb-1">
              Assumptions
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-amber-400">
                {spec.assumptions.length}
              </span>
              <span className="text-xs text-slate-400">active</span>
            </div>
            <p className="mt-2 text-[10px] text-slate-400">
              {coverage.assumption_resolution_pct}% resolution rate
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#111827] border border-[#1F2937]">
            <span className="text-[11px] font-semibold uppercase text-slate-400 block mb-1">
              Validation Health
            </span>
            <div className="flex items-baseline gap-2">
              {validation && validation.is_valid ? (
                <span className="text-2xl font-bold font-mono text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-5 h-5" /> Valid
                </span>
              ) : (
                <span className="text-2xl font-bold font-mono text-rose-400 flex items-center gap-1.5">
                  <AlertCircle className="w-5 h-5" /> {validation?.errors} Err
                </span>
              )}
            </div>
            <p className="mt-2 text-[10px] text-slate-400">
              {validation?.warnings || 0} warnings flagged
            </p>
          </div>
        </div>
      )}

      {/* Main Tab Navigation */}
      {spec && (
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-[#1F2937] pb-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab("requirements")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "requirements"
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Layers className="w-4 h-4" />
                Requirements ({spec.requirements.length})
              </button>

              <button
                onClick={() => setActiveTab("graph")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "graph"
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Network className="w-4 h-4" />
                Traceability Graph ({graph?.nodes.length || 0})
              </button>

              <button
                onClick={() => setActiveTab("validation")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "validation"
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <ShieldCheck className="w-4 h-4" />
                Validation ({validation?.findings.length || 0})
              </button>

              <button
                onClick={() => setActiveTab("matrix")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "matrix"
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <ListChecks className="w-4 h-4" />
                Traceability Matrix
              </button>
            </div>

            <div className="text-[11px] text-slate-400 font-mono">
              Spec ID: {spec.id} (v{spec.version})
            </div>
          </div>

          {/* TAB 1: REQUIREMENTS LIST */}
          {activeTab === "requirements" && (
            <div className="space-y-4">
              {/* Category Pills & Search */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-1.5 flex-wrap">
                  {["all", "functional", "technical_constraint", "nonfunctional", "security"].map((cat) => (
                    <button
                      key={cat}
                      onClick={() => setCategoryFilter(cat)}
                      className={`px-2.5 py-1 rounded text-xs capitalize transition ${
                        categoryFilter === cat
                          ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                          : "bg-[#111827] text-slate-400 border border-[#1F2937] hover:text-slate-200"
                      }`}
                    >
                      {cat.replace("_", " ")}
                    </button>
                  ))}
                </div>

                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    placeholder="Search requirements..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-[#0B0F17] border border-[#1F2937] rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              {/* Requirement Cards */}
              <div className="space-y-3">
                {filteredRequirements.map((req) => (
                  <RequirementCard
                    key={req.id}
                    req={req}
                    onAnalyzeImpact={() => {
                      setActiveTab("graph");
                      handleSelectNode(req.id);
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: TRACEABILITY GRAPH */}
          {activeTab === "graph" && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Visual Graph View */}
                <div className="lg:col-span-2 border border-[#1F2937] bg-[#111827] rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-200">NetworkX Directed Graph View</span>
                      {graph?.has_cycles ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/10 border border-rose-500/30 text-rose-400">
                          Cycles Detected
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                          DAG Verified (Acyclic)
                        </span>
                      )}
                    </div>
                    <span className="text-slate-400 text-[11px]">Click any node to inspect blast radius</span>
                  </div>

                  {graph && (
                    <InteractiveGraphSVG
                      graph={graph}
                      selectedNodeId={selectedNodeId}
                      impactReport={impactReport}
                      onSelectNode={handleSelectNode}
                    />
                  )}
                </div>

                {/* Impact Analysis Drawer */}
                <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                      Blast Radius Impact Analysis
                    </h3>
                    {impactReport && (
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
                          impactReport.risk_level === "critical"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                            : impactReport.risk_level === "high"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        }`}
                      >
                        {impactReport.risk_level} Risk
                      </span>
                    )}
                  </div>

                  {loadingImpact ? (
                    <div className="p-6 text-center text-xs text-slate-400">
                      <RotateCcw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
                      Computing blast radius...
                    </div>
                  ) : impactReport ? (
                    <div className="space-y-3 text-xs">
                      <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                        <span className="text-[11px] text-slate-400 block mb-0.5">Target Requirement</span>
                        <span className="font-mono text-cyan-400 font-semibold">{impactReport.target_req_id}</span>
                      </div>

                      <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                        <span className="text-[11px] text-slate-400 block mb-1">
                          Downstream Dependents ({impactReport.downstream_dependents.length})
                        </span>
                        <p className="text-[11px] text-slate-400 mb-2">
                          Requirements that directly or transitively depend on this item. If modified, these may require regression verification.
                        </p>
                        {impactReport.downstream_dependents.length === 0 ? (
                          <span className="text-slate-400 italic text-[11px]">No downstream dependents (leaf node).</span>
                        ) : (
                          <div className="flex flex-wrap gap-1.5">
                            {impactReport.downstream_dependents.map((dep) => (
                              <span
                                key={dep}
                                className="px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 font-mono text-[11px]"
                              >
                                {dep}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                        <span className="text-[11px] text-slate-400 block mb-1">
                          Upstream Prerequisites ({impactReport.upstream_dependencies.length})
                        </span>
                        {impactReport.upstream_dependencies.length === 0 ? (
                          <span className="text-slate-400 italic text-[11px]">No upstream dependencies.</span>
                        ) : (
                          <div className="flex flex-wrap gap-1.5">
                            {impactReport.upstream_dependencies.map((dep) => (
                              <span
                                key={dep}
                                className="px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-mono text-[11px]"
                              >
                                {dep}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="p-6 text-center text-xs text-slate-400">
                      Select a requirement node in the graph to evaluate upstream and downstream change risks.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: VALIDATION FINDINGS */}
          {activeTab === "validation" && validation && (
            <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                  Validation & Quality Findings ({validation.total_findings})
                </h3>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-rose-400">{validation.errors} Errors</span>
                  <span className="text-amber-400">{validation.warnings} Warnings</span>
                  <span className="text-cyan-400">{validation.info} Info</span>
                </div>
              </div>

              {validation.findings.length === 0 ? (
                <div className="p-6 text-center text-xs text-emerald-400 border border-emerald-500/20 rounded-lg bg-emerald-500/5">
                  <CheckCircle2 className="w-6 h-6 mx-auto mb-1.5" />
                  All requirements passed validation rules with zero errors or warnings!
                </div>
              ) : (
                <div className="space-y-2.5">
                  {validation.findings.map((f, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-lg border text-xs ${
                        f.severity === "error"
                          ? "bg-rose-500/5 border-rose-500/30 text-rose-300"
                          : f.severity === "warning"
                          ? "bg-amber-500/5 border-amber-500/30 text-amber-300"
                          : "bg-cyan-500/5 border-cyan-500/30 text-cyan-300"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          {f.severity === "error" ? (
                            <AlertCircle className="w-4 h-4 text-rose-400" />
                          ) : f.severity === "warning" ? (
                            <AlertTriangle className="w-4 h-4 text-amber-400" />
                          ) : (
                            <Info className="w-4 h-4 text-cyan-400" />
                          )}
                          <span className="font-mono font-semibold">{f.rule_id}</span>
                          {f.target_req_id && (
                            <span className="px-1.5 py-0.2 rounded bg-[#0B0F17] font-mono text-[10px] text-slate-300 border border-[#1F2937]">
                              {f.target_req_id}
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] uppercase font-mono tracking-wider opacity-80">
                          {f.severity}
                        </span>
                      </div>
                      <p className="text-slate-200 mt-1">{f.message}</p>
                      <div className="mt-2 text-[11px] text-slate-400 flex items-start gap-1.5">
                        <ArrowRight className="w-3.5 h-3.5 shrink-0 mt-0.5 text-slate-400" />
                        <span>{f.suggestion}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: TRACEABILITY MATRIX */}
          {activeTab === "matrix" && (
            <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                    Bidirectional Traceability Matrix
                  </h3>
                  <p className="text-xs text-slate-400">
                    Traces source requirements through acceptance criteria and future Phase 4 code/test artifacts.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border border-[#1F2937]">
                  <thead className="bg-[#0B0F17] text-slate-400 font-semibold border-b border-[#1F2937]">
                    <tr>
                      <th className="p-3">Req ID</th>
                      <th className="p-3">Title & Category</th>
                      <th className="p-3">Status</th>
                      <th className="p-3">Acceptance Criteria</th>
                      <th className="p-3">Dependencies</th>
                      <th className="p-3">Code Link</th>
                      <th className="p-3">Test Link</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1F2937] text-slate-300">
                    {spec.requirements.map((r) => (
                      <tr key={r.id} className="hover:bg-[#1E293B]/40 transition">
                        <td className="p-3 font-mono text-cyan-400 font-semibold">{r.id}</td>
                        <td className="p-3">
                          <span className="font-medium text-slate-200 block">{r.title}</span>
                          <span className="text-[11px] text-slate-400 capitalize">{r.category.replace("_", " ")}</span>
                        </td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono capitalize ${
                              r.status === "explicit"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                : "bg-purple-500/10 text-purple-400 border border-purple-500/30"
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="p-3">
                          <span className="font-mono text-slate-300">
                            {r.acceptance_criteria.length} criteria
                          </span>
                        </td>
                        <td className="p-3">
                          {r.depends_on.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {r.depends_on.map((d) => (
                                <span key={d} className="px-1.5 py-0.5 rounded bg-[#0B0F17] font-mono text-[10px] text-slate-400">
                                  {d}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-400 text-[11px]">—</span>
                          )}
                        </td>
                        <td className="p-3 font-mono text-[11px] text-slate-400">Pending Phase 4</td>
                        <td className="p-3 font-mono text-[11px] text-slate-400">Pending Phase 4</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937] text-[11px] text-slate-400 leading-relaxed">
                <span className="font-semibold text-slate-300 block mb-0.5">Integrity Note</span>
                PromptForge AI avoids fabricating code and unit test coverage. The matrix truthfully reports execution links as <strong>Pending Phase 4</strong> until code synthesis and docker sandbox verification are initiated.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Sub-component: Requirement Card
interface RequirementCardProps {
  req: RequirementItem;
  onAnalyzeImpact: () => void;
}

const RequirementCard: React.FC<RequirementCardProps> = ({ req, onAnalyzeImpact }) => {
  return (
    <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-4 space-y-3 hover:border-slate-700 transition">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0">
            {req.id}
          </span>
          <div>
            <h4 className="text-xs font-semibold text-white">{req.title}</h4>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">{req.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0 flex-wrap justify-end">
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono capitalize ${
              req.category === "functional"
                ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                : req.category === "security"
                ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                : req.category === "technical_constraint"
                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                : "bg-purple-500/10 text-purple-400 border border-purple-500/20"
            }`}
          >
            {req.category.replace("_", " ")}
          </span>

          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
              req.priority === "critical"
                ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                : req.priority === "high"
                ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                : "bg-slate-700/40 text-slate-400 border border-slate-600/30"
            }`}
          >
            {req.priority}
          </span>

          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono capitalize flex items-center gap-1 ${
              req.status === "explicit"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                : "bg-purple-500/10 text-purple-400 border border-purple-500/30"
            }`}
          >
            {req.status === "inferred" && <Sparkles className="w-2.5 h-2.5" />}
            {req.status}
          </span>
        </div>
      </div>

      {/* Assumptions if inferred */}
      {req.assumptions.length > 0 && (
        <div className="p-2.5 rounded-lg bg-purple-500/5 border border-purple-500/20 text-xs">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-purple-400 block mb-1">
            Underlying Assumptions ({req.assumptions.length})
          </span>
          <ul className="space-y-1 text-slate-300 text-[11px]">
            {req.assumptions.map((asm) => (
              <li key={asm.id} className="flex items-start gap-1.5">
                <span className="font-mono text-purple-400 shrink-0">{asm.id}:</span>
                <span>{asm.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Acceptance Criteria */}
      <div className="space-y-1.5 pt-1">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">
          Acceptance Criteria ({req.acceptance_criteria.length})
        </span>
        <div className="space-y-1">
          {req.acceptance_criteria.map((ac) => (
            <div
              key={ac.id}
              className="flex items-start gap-2 p-2 rounded bg-[#0B0F17] border border-[#1F2937] text-xs text-slate-300"
            >
              <span className="font-mono text-[10px] text-cyan-400 shrink-0 mt-0.5">{ac.id}</span>
              <span className="flex-1 text-[11px]">{ac.description}</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1E293B] text-slate-400 border border-[#334155]/60 uppercase">
                {ac.verification_type.replace("_", " ")}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Card Footer */}
      <div className="flex items-center justify-between text-xs pt-2 border-t border-[#1F2937]/60">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-400">Dependencies:</span>
          {req.depends_on.length > 0 ? (
            req.depends_on.map((dep) => (
              <span key={dep} className="px-1.5 py-0.5 rounded bg-[#0B0F17] font-mono text-[10px] text-cyan-400 border border-[#1F2937]">
                {dep}
              </span>
            ))
          ) : (
            <span className="text-[11px] text-slate-400 italic">None</span>
          )}
        </div>

        <button
          onClick={onAnalyzeImpact}
          className="text-cyan-400 hover:text-cyan-300 text-[11px] font-medium flex items-center gap-1 transition"
        >
          Inspect Blast Radius <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};

// Sub-component: Interactive SVG Graph Renderer
interface InteractiveGraphSVGProps {
  graph: TraceabilityGraph;
  selectedNodeId: string | null;
  impactReport: ImpactAnalysisReport | null;
  onSelectNode: (nodeId: string) => void;
}

const InteractiveGraphSVG: React.FC<InteractiveGraphSVGProps> = ({
  graph,
  selectedNodeId,
  impactReport,
  onSelectNode,
}) => {
  // Compute hierarchical node coordinates
  const nodePositions = useMemo(() => {
    const pos: Record<string, { x: number; y: number; color: string }> = {};
    const width = 650;

    // Prompt Root at top
    pos["PROMPT-ROOT"] = { x: width / 2, y: 50, color: "#38bdf8" };

    // Categorize remaining nodes
    const reqNodes = graph.nodes.filter((n) => n.id !== "PROMPT-ROOT");
    const count = reqNodes.length;

    reqNodes.forEach((node, index) => {
      // Distribute in two rows
      const isTopRow = index < Math.ceil(count / 2);
      const rowCount = isTopRow ? Math.ceil(count / 2) : Math.floor(count / 2);
      const colIndex = isTopRow ? index : index - Math.ceil(count / 2);

      const spacing = width / (rowCount + 1);
      const x = spacing * (colIndex + 1);
      const y = isTopRow ? 160 : 270;

      let color = "#38bdf8"; // default cyan
      if (node.category === "security") color = "#f43f5e";
      else if (node.category === "technical_constraint") color = "#fbbf24";
      else if (node.category === "nonfunctional") color = "#a855f7";

      pos[node.id] = { x, y, color };
    });

    return pos;
  }, [graph]);

  return (
    <div className="w-full overflow-x-auto bg-[#0B0F17] rounded-lg border border-[#1F2937] p-2 flex justify-center">
      <svg width="680" height="340" className="select-none font-sans">
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="22"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#4B5563" />
          </marker>
          <marker
            id="arrow-active"
            viewBox="0 0 10 10"
            refX="22"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#f43f5e" />
          </marker>
        </defs>

        {/* Directed Edges */}
        {graph.edges.map((edge, idx) => {
          const from = nodePositions[edge.source];
          const to = nodePositions[edge.target];
          if (!from || !to) return null;

          const isImpactEdge =
            impactReport &&
            ((edge.source === selectedNodeId && impactReport.upstream_dependencies.includes(edge.target)) ||
              (impactReport.downstream_dependents.includes(edge.source) && edge.target === selectedNodeId));

          return (
            <line
              key={idx}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={isImpactEdge ? "#f43f5e" : "#374151"}
              strokeWidth={isImpactEdge ? "2" : "1.2"}
              strokeDasharray={edge.relation === "depends_on" ? "4,4" : undefined}
              markerEnd={isImpactEdge ? "url(#arrow-active)" : "url(#arrow)"}
              className="transition-all"
            />
          );
        })}

        {/* Nodes */}
        {graph.nodes.map((node) => {
          const pos = nodePositions[node.id];
          if (!pos) return null;

          const isSelected = selectedNodeId === node.id;
          const isDownstream = impactReport?.downstream_dependents.includes(node.id);
          const isUpstream = impactReport?.upstream_dependencies.includes(node.id);

          let strokeColor = pos.color;
          let fillColor = "#111827";

          if (isSelected) {
            strokeColor = "#06b6d4";
            fillColor = "#164e63";
          } else if (isDownstream) {
            strokeColor = "#f43f5e";
            fillColor = "#4c0519";
          } else if (isUpstream) {
            strokeColor = "#38bdf8";
            fillColor = "#082f49";
          }

          return (
            <g
              key={node.id}
              onClick={() => onSelectNode(node.id)}
              className="cursor-pointer group"
            >
              <circle
                cx={pos.x}
                cy={pos.y}
                r="18"
                fill={fillColor}
                stroke={strokeColor}
                strokeWidth={isSelected ? "3" : "1.5"}
                className="transition-all"
              />
              <text
                x={pos.x}
                y={pos.y + 4}
                textAnchor="middle"
                fontSize="9"
                fontWeight="bold"
                fill="#F3F4F6"
                className="font-mono pointer-events-none"
              >
                {node.id === "PROMPT-ROOT" ? "ROOT" : node.id.replace("REQ-", "R")}
              </text>
              <text
                x={pos.x}
                y={pos.y + 30}
                textAnchor="middle"
                fontSize="8.5"
                fill={isSelected ? "#38bdf8" : "#9CA3AF"}
                className="pointer-events-none"
              >
                {node.label.length > 14 ? node.label.substring(0, 13) + "…" : node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
