import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Upload,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Play,
  RotateCcw,
  Check,
  Zap,
  Terminal,
  FolderGit2,
} from "lucide-react";
import {
  ingestProjectArchive,
  ingestProjectJson,
  listProjects,
  getProject,
  linkRequirements,
  getProjectTraceability,
  confirmLink,
  triggerVerificationRun,
  getSpecificationEvidence,
  getDockerStatus,
} from "../api/verification";
import { listSpecifications } from "../api/requirement";
import {
  DockerStatusResponse,
  ProjectIngestionReport,
  ProjectSummary,
  RequirementEvidenceReport,
  TraceabilityLink,
  VerificationRun,
} from "../types/verification";
import { SpecificationSummary } from "../types/requirement";

interface SamplePreset {
  name: string;
  files: Record<string, string>;
}

// Built-in presets for instant demonstration and developer testing
const SAMPLE_PRESETS: SamplePreset[] = [
  {
    name: "LRU Cache Service (Passing Tests)",
    files: {
      "src/lru_cache.py":
        "class LRUCache:\n    \"\"\"Thread-safe LRU Cache implementing REQ-001.\"\"\"\n    def __init__(self, capacity: int):\n        self.capacity = capacity\n        self.cache = {}\n    def get(self, key):\n        return self.cache.get(key, None)\n    def put(self, key, value):\n        self.cache[key] = value\n",
      "tests/test_lru_cache.py":
        "from src.lru_cache import LRUCache\ndef test_req_001_cache_operations():\n    cache = LRUCache(2)\n    cache.put('x', 10)\n    assert cache.get('x') == 10\n",
      "requirements.txt": "pytest>=8.0.0\n",
      "README.md": "# LRU Cache Module\n",
    },
  },
  {
    name: "User Authentication API (With Failing Test)",
    files: {
      "src/auth_service.py":
        "def hash_password(pwd: str) -> str:\n    return f'hashed_{pwd}'\ndef verify_token(token: str) -> bool:\n    # Bug: fails to check signature (violates REQ-001)\n    return False\n",
      "tests/test_auth.py":
        "from src.auth_service import verify_token\ndef test_req_001_valid_token_verification():\n    assert verify_token('valid.jwt.token') is True\n",
      "requirements.txt": "pytest>=8.0.0\n",
    },
  },
];

export const VerificationPage: React.FC = () => {
  // Docker availability telemetry
  const [dockerStatus, setDockerStatus] = useState<DockerStatusResponse | null>(null);

  // Ingestion & Project State
  const [project, setProject] = useState<ProjectIngestionReport | null>(null);
  const [projectsList, setProjectsList] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Specification & Linking State
  const [specList, setSpecList] = useState<SpecificationSummary[]>([]);
  const [selectedSpecId, setSelectedSpecId] = useState<string>("");
  const [links, setLinks] = useState<TraceabilityLink[]>([]);
  const [loadingLinks, setLoadingLinks] = useState<boolean>(false);

  // Execution & Evidence State
  const [latestRun, setLatestRun] = useState<VerificationRun | null>(null);
  const [runningTest, setRunningTest] = useState<boolean>(false);
  const [evidence, setEvidence] = useState<RequirementEvidenceReport | null>(null);

  // Active view tab
  const [activeTab, setActiveTab] = useState<"artifacts" | "traceability" | "run" | "evidence">("artifacts");

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [dStatus, pList, sList] = await Promise.all([
        getDockerStatus().catch(() => ({
          docker_available: false,
          message: "Docker daemon connection failed.",
          fail_closed_policy: "Host fallback prohibited.",
        })),
        listProjects().catch(() => []),
        listSpecifications().catch(() => ({ specifications: [], total: 0 })),
      ]);
      setDockerStatus(dStatus);
      setProjectsList(pList);
      setSpecList(sList.specifications);
    } catch {
      // Non-fatal
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      const res = await ingestProjectArchive(file);
      setProject(res);
      setSelectedProjectId(res.project_id);
      setLinks([]);
      setLatestRun(null);
      setEvidence(null);
      await loadInitialData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload archive.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadPreset = async (presetIdx: number) => {
    const preset = SAMPLE_PRESETS[presetIdx];
    setLoading(true);
    setError(null);
    try {
      const res = await ingestProjectJson(preset.files, preset.name);
      setProject(res);
      setSelectedProjectId(res.project_id);
      setLinks([]);
      setLatestRun(null);
      setEvidence(null);
      await loadInitialData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load preset.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectExistingProject = async (projId: string) => {
    if (!projId) return;
    setSelectedProjectId(projId);
    setLoading(true);
    setError(null);
    try {
      const p = await getProject(projId);
      setProject(p);
      const existingLinks = await getProjectTraceability(projId);
      setLinks(existingLinks);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load project.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleLinkRequirements = async () => {
    if (!project || !selectedSpecId) return;
    setLoadingLinks(true);
    setError(null);
    try {
      const generatedLinks = await linkRequirements(project.project_id, selectedSpecId);
      setLinks(generatedLinks);
      setActiveTab("traceability");
      // Also refresh evidence
      const ev = await getSpecificationEvidence(selectedSpecId, project.project_id);
      setEvidence(ev);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to link requirements.";
      setError(msg);
    } finally {
      setLoadingLinks(false);
    }
  };

  const handleToggleConfirmLink = async (linkId: string, currentConfirmed: boolean) => {
    if (!project) return;
    try {
      const updated = await confirmLink(project.project_id, linkId, !currentConfirmed);
      setLinks((prev) => prev.map((l) => (l.id === linkId ? updated : l)));
      if (selectedSpecId) {
        const ev = await getSpecificationEvidence(selectedSpecId, project.project_id);
        setEvidence(ev);
      }
    } catch {
      // Non-fatal
    }
  };

  const handleRunVerification = async () => {
    if (!project) return;
    setRunningTest(true);
    setError(null);
    try {
      const run = await triggerVerificationRun(project.project_id, selectedSpecId || undefined);
      setLatestRun(run);
      setActiveTab("run");

      // Update evidence report
      if (selectedSpecId) {
        const ev = await getSpecificationEvidence(selectedSpecId, project.project_id);
        setEvidence(ev);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to run verification.";
      setError(msg);
    } finally {
      setRunningTest(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-white">Code Evidence & Automated Verification</h2>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  Phase 4 Active
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Safe archive ingestion, SHA-256 fingerprinting, requirement-to-code traceability, and fail-closed isolated Docker verification.
              </p>
            </div>
          </div>

          {/* Docker Status Telemetry Pill */}
          <div className="flex items-center gap-2">
            {dockerStatus ? (
              dockerStatus.docker_available ? (
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Docker Sandbox Ready
                </div>
              ) : (
                <div
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-mono"
                  title={dockerStatus.message}
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Docker Offline (Fail-Closed Active)
                </div>
              )
            ) : null}
          </div>
        </div>

        {/* Security Policy Reminder */}
        <div className="p-3.5 rounded-lg bg-[#0B0F17] border border-[#1F2937] text-xs text-slate-400 flex items-start gap-2.5">
          <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold text-slate-200">Strict Isolation & Fail-Closed Guarantee</span>
            <p className="text-[11px] leading-relaxed">
              Untrusted uploaded code is <strong>never executed directly on the host machine</strong>. When the Docker daemon is offline, verification runs fail closed rather than unsafely falling back to host execution.
            </p>
          </div>
        </div>
      </div>

      {/* Ingestion & Selection Control Panel */}
      <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Project Ingestion & Workspaces
            </h3>
            <p className="text-xs text-slate-400">
              Upload a source ZIP archive or select a preset module.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Existing project picker */}
            {projectsList.length > 0 && (
              <select
                aria-label="Select Ingested Project"
                value={selectedProjectId}
                onChange={(e) => handleSelectExistingProject(e.target.value)}
                className="bg-[#0B0F17] border border-[#1F2937] text-xs text-slate-300 rounded-lg px-3 py-1.5 focus:border-cyan-500 focus:outline-none"
              >
                <option value="">-- Load Existing Project ({projectsList.length}) --</option>
                {projectsList.map((p) => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.name} ({p.total_files} files)
                  </option>
                ))}
              </select>
            )}

            {/* Presets */}
            {SAMPLE_PRESETS.map((preset, idx) => (
              <button
                key={idx}
                onClick={() => handleLoadPreset(idx)}
                disabled={loading}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[#0B0F17] hover:bg-[#1E293B] border border-[#1F2937] text-slate-300 text-xs font-medium transition"
              >
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                {preset.name.split(" ")[0]} Preset
              </button>
            ))}

            {/* Upload ZIP */}
            <label className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-semibold cursor-pointer transition">
              <Upload className="w-3.5 h-3.5" />
              Upload ZIP
              <input
                type="file"
                accept=".zip"
                onChange={handleFileUpload}
                disabled={loading}
                className="hidden"
              />
            </label>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Project Ingestion Overview Bar */}
        {project && (
          <div className="p-4 rounded-lg bg-[#0B0F17] border border-[#1F2937] space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1F2937]/60 pb-2">
              <div className="flex items-center gap-2">
                <FolderGit2 className="w-4 h-4 text-cyan-400" />
                <span className="font-semibold text-slate-200 text-xs">{project.name}</span>
                <span className="text-[10px] font-mono text-slate-400">({project.project_id})</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                <span>{project.total_files} files</span>
                <span>•</span>
                <span>{project.total_size_bytes} bytes</span>
                <span>•</span>
                <span className="text-emerald-400">
                  {project.detected_test_frameworks.join(", ") || "No tests detected"}
                </span>
              </div>
            </div>

            {project.warnings.length > 0 && (
              <div className="space-y-1">
                {project.warnings.map((w, idx) => (
                  <div key={idx} className="text-[11px] text-amber-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3 h-3 shrink-0" />
                    <span>{w}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Link to Specification Control */}
            <div className="flex items-center justify-between gap-3 pt-2">
              <div className="flex items-center gap-2 flex-1">
                <span className="text-xs text-slate-400 shrink-0">Link with Phase 3 Spec:</span>
                <select
                  aria-label="Link Phase 3 Specification"
                  value={selectedSpecId}
                  onChange={(e) => setSelectedSpecId(e.target.value)}
                  className="bg-[#111827] border border-[#1F2937] text-xs text-slate-300 rounded px-2.5 py-1.5 focus:border-cyan-500 focus:outline-none flex-1 max-w-md"
                >
                  <option value="">-- Choose Specification ({specList.length}) --</option>
                  {specList.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title} ({s.total_requirements} requirements)
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleLinkRequirements}
                  disabled={loadingLinks || !selectedSpecId}
                  className="px-3 py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-xs font-semibold transition disabled:opacity-50"
                >
                  {loadingLinks ? "Linking..." : "Generate Links"}
                </button>

                <button
                  onClick={handleRunVerification}
                  disabled={runningTest}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-semibold transition disabled:opacity-50"
                >
                  {runningTest ? (
                    <>
                      <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                      Running Sandbox...
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" />
                      Execute Verification
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Tabs Navigation */}
      {project && (
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-[#1F2937] pb-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab("artifacts")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "artifacts"
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <FileCode className="w-4 h-4" />
                Artifact Inventory ({project.ingested_artifacts.length})
              </button>

              <button
                onClick={() => setActiveTab("traceability")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "traceability"
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <ShieldCheck className="w-4 h-4" />
                Traceability Links ({links.length})
              </button>

              <button
                onClick={() => setActiveTab("run")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "run"
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Terminal className="w-4 h-4" />
                Sandbox Run Results {latestRun && `(${latestRun.status})`}
              </button>

              <button
                onClick={() => setActiveTab("evidence")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "evidence"
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <CheckCircle2 className="w-4 h-4" />
                Requirement Evidence {evidence && `(${evidence.verification_coverage_pct}%)`}
              </button>
            </div>
          </div>

          {/* TAB 1: ARTIFACT INVENTORY */}
          {activeTab === "artifacts" && (
            <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                    Inventoried Source & Test Artifacts
                  </h3>
                  <p className="text-xs text-slate-400">
                    Fingerprinted files with SHA-256 hashes and extracted AST symbols.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border border-[#1F2937]">
                  <thead className="bg-[#0B0F17] text-slate-400 font-semibold border-b border-[#1F2937]">
                    <tr>
                      <th className="p-3">Artifact ID</th>
                      <th className="p-3">Path & Language</th>
                      <th className="p-3">Type</th>
                      <th className="p-3">SHA-256 Hash</th>
                      <th className="p-3">LOC</th>
                      <th className="p-3">Extracted AST Symbols</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1F2937] text-slate-300 font-mono text-[11px]">
                    {project.ingested_artifacts.map((art) => (
                      <tr key={art.id} className="hover:bg-[#1E293B]/40 transition">
                        <td className="p-3 text-cyan-400 font-semibold">{art.id}</td>
                        <td className="p-3">
                          <span className="text-slate-200 font-sans font-medium block">
                            {art.relative_path}
                          </span>
                          <span className="text-slate-400 text-[10px] uppercase">
                            {art.language}
                          </span>
                        </td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] uppercase ${
                              art.file_type === "test_file"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : art.file_type === "manifest"
                                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                : "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                            }`}
                          >
                            {art.file_type.replace("_", " ")}
                          </span>
                        </td>
                        <td className="p-3 text-slate-400 text-[10px]" title={art.sha256}>
                          {art.sha256.substring(0, 16)}...
                        </td>
                        <td className="p-3 text-slate-300">{art.line_count}</td>
                        <td className="p-3">
                          {art.symbols.length > 0 ? (
                            <div className="flex flex-wrap gap-1 max-w-xs">
                              {art.symbols.map((sym, sidx) => (
                                <span
                                  key={sidx}
                                  className="px-1.5 py-0.5 rounded bg-[#0B0F17] text-slate-300 text-[10px] border border-[#1F2937]"
                                >
                                  {sym}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-400 italic font-sans text-[11px]">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: TRACEABILITY LINKS */}
          {activeTab === "traceability" && (
            <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                    Requirement-to-Code Traceability Links ({links.length})
                  </h3>
                  <p className="text-xs text-slate-400">
                    Candidate links identified via AST symbols and requirement tags. Confirmed links provide verified traceability.
                  </p>
                </div>
              </div>

              {links.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400 border border-[#1F2937] rounded-lg">
                  No traceability links generated yet. Select a Phase 3 Specification above and click &quot;Generate Links&quot;.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border border-[#1F2937]">
                    <thead className="bg-[#0B0F17] text-slate-400 font-semibold border-b border-[#1F2937]">
                      <tr>
                        <th className="p-3">Link ID</th>
                        <th className="p-3">Requirement</th>
                        <th className="p-3">Artifact & Symbol</th>
                        <th className="p-3">Type</th>
                        <th className="p-3">Origin & Conf.</th>
                        <th className="p-3">Confirmation State</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1F2937] text-slate-300 text-[11px]">
                      {links.map((link) => (
                        <tr key={link.id} className="hover:bg-[#1E293B]/40 transition">
                          <td className="p-3 font-mono text-cyan-400 font-semibold">{link.id}</td>
                          <td className="p-3 font-mono text-slate-200">{link.requirement_id}</td>
                          <td className="p-3">
                            <span className="font-mono text-slate-200 block">{link.artifact_path}</span>
                            {link.symbol_name && (
                              <span className="text-[10px] text-cyan-400 font-mono">
                                sym: {link.symbol_name}
                              </span>
                            )}
                            <p className="text-[10px] text-slate-400 mt-0.5">{link.rationale}</p>
                          </td>
                          <td className="p-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono capitalize ${
                                link.link_type.includes("test")
                                  ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                                  : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                              }`}
                            >
                              {link.link_type.replace("_", " ")}
                            </span>
                          </td>
                          <td className="p-3">
                            <span className="capitalize block">{link.link_origin.replace("_", " ")}</span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {Math.round(link.confidence * 100)}% confidence
                            </span>
                          </td>
                          <td className="p-3">
                            <button
                              onClick={() => handleToggleConfirmLink(link.id, link.is_confirmed)}
                              className={`flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-semibold transition ${
                                link.is_confirmed
                                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                                  : "bg-[#1E293B] text-slate-400 border border-[#334155] hover:text-slate-200"
                              }`}
                            >
                              {link.is_confirmed ? (
                                <>
                                  <Check className="w-3 h-3 text-emerald-400" /> Confirmed
                                </>
                              ) : (
                                "Candidate (Click to Confirm)"
                              )}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: VERIFICATION RUN */}
          {activeTab === "run" && latestRun && (
            <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal className="w-5 h-5 text-cyan-400" />
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                      Sandbox Execution Run: {latestRun.id}
                    </h3>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Completed at {latestRun.completed_at || latestRun.created_at}
                    </span>
                  </div>
                </div>

                <span
                  className={`px-3 py-1 rounded-full text-xs font-mono uppercase font-semibold ${
                    latestRun.status === "passed"
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                      : latestRun.status === "failed"
                      ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                      : latestRun.status === "unavailable"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                      : "bg-slate-700 text-slate-300"
                  }`}
                >
                  {latestRun.status}
                </span>
              </div>

              {/* Run Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                  <span className="text-[10px] uppercase text-slate-400 block mb-0.5">Total Tests</span>
                  <span className="text-xl font-bold font-mono text-cyan-400">{latestRun.total_tests}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                  <span className="text-[10px] uppercase text-slate-400 block mb-0.5">Passed Tests</span>
                  <span className="text-xl font-bold font-mono text-emerald-400">{latestRun.passed_tests}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                  <span className="text-[10px] uppercase text-slate-400 block mb-0.5">Failed Tests</span>
                  <span className="text-xl font-bold font-mono text-rose-400">{latestRun.failed_tests}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937]">
                  <span className="text-[10px] uppercase text-slate-400 block mb-0.5">Execution Duration</span>
                  <span className="text-xl font-bold font-mono text-slate-300">{latestRun.duration_ms} ms</span>
                </div>
              </div>

              {/* Sandbox Security Environment Note */}
              <div className="p-3 rounded-lg bg-[#0B0F17] border border-[#1F2937] text-[11px] text-slate-400">
                {latestRun.docker_available ? (
                  <span className="text-emerald-400">
                    Executed in non-networked container (--network none, 512MB RAM cap, read-only volume).
                  </span>
                ) : (
                  <span className="text-amber-400">
                    Execution blocked: Docker sandbox daemon is offline. Host fallback execution was prevented by security policy.
                  </span>
                )}
              </div>

              {/* Terminal Logs Viewer */}
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-slate-300">Container Stdout / Stderr Logs</span>
                <pre className="p-4 rounded-lg bg-[#05080E] border border-[#1F2937] text-slate-300 font-mono text-xs overflow-x-auto max-h-64 whitespace-pre-wrap">
                  {latestRun.stdout || latestRun.stderr || "(No terminal output captured)"}
                </pre>
              </div>
            </div>
          )}

          {/* TAB 4: REQUIREMENT EVIDENCE & TRUTHFUL COVERAGE */}
          {activeTab === "evidence" && evidence && (
            <div className="border border-[#1F2937] bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                    Requirement-Level Verification Evidence
                  </h3>
                  <p className="text-xs text-slate-400">
                    A requirement is marked Verified only when backed by passing automated test executions and clean static checks.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-300">Verified Coverage:</span>
                  <span className="text-lg font-bold font-mono text-emerald-400">
                    {evidence.verification_coverage_pct}%
                  </span>
                </div>
              </div>

              {/* Requirement Verdicts Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border border-[#1F2937]">
                  <thead className="bg-[#0B0F17] text-slate-400 font-semibold border-b border-[#1F2937]">
                    <tr>
                      <th className="p-3">Req ID</th>
                      <th className="p-3">Requirement Title</th>
                      <th className="p-3">Code / Test Links</th>
                      <th className="p-3">Verification Verdict</th>
                      <th className="p-3">Evidence Rationale</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1F2937] text-slate-300 text-[11px]">
                    {evidence.verdicts.map((verd) => (
                      <tr key={verd.requirement_id} className="hover:bg-[#1E293B]/40 transition">
                        <td className="p-3 font-mono text-cyan-400 font-semibold">{verd.requirement_id}</td>
                        <td className="p-3 font-medium text-slate-200">{verd.requirement_title}</td>
                        <td className="p-3 font-mono text-[10px]">
                          <span className="text-blue-400">{verd.linked_code_count} code</span>
                          <span className="text-slate-500 mx-1">/</span>
                          <span className="text-purple-400">{verd.linked_test_count} tests</span>
                        </td>
                        <td className="p-3">
                          <span
                            className={`px-2.5 py-0.5 rounded text-[10px] font-mono uppercase font-semibold flex items-center gap-1 w-fit ${
                              verd.verdict === "verified"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                : verd.verdict === "failed"
                                ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                                : "bg-slate-700/40 text-slate-400 border border-slate-600/30"
                            }`}
                          >
                            {verd.verdict === "verified" && <CheckCircle2 className="w-3 h-3" />}
                            {verd.verdict === "failed" && <AlertCircle className="w-3 h-3" />}
                            {verd.verdict}
                          </span>
                        </td>
                        <td className="p-3 text-slate-300 text-[11px] leading-relaxed">
                          {verd.rationale}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Explanatory notes */}
              <div className="p-3.5 rounded-lg bg-[#0B0F17] border border-[#1F2937] space-y-1">
                <span className="text-[11px] font-semibold text-slate-300 block mb-1">Coverage Formula Note</span>
                {evidence.notes.map((n, idx) => (
                  <p key={idx} className="text-[11px] text-slate-400 leading-relaxed">
                    • {n}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
