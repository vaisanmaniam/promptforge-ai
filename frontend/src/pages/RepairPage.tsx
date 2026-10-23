import React, { useState, useEffect } from 'react';
import {
  Wrench,
  AlertTriangle,
  CheckCircle,
  Play,
  Layers,
  Sparkles,
  GitCommit,
  RotateCcw,
  ShieldCheck,
  Terminal,
  RefreshCw,
  Cpu,
  ChevronDown,
  ChevronUp,
  FileCode,
  History,
  Check,
  X,
  FileDiff,
} from 'lucide-react';
import {
  analyzeRunFailures,
  generateProposal,
  approveProposal,
  rejectProposal,
  applyProposal,
  verifyProposal,
  rollbackProposal,
  getRepairHistory,
  getRepairRuntimeStatus,
  listProposals,
} from '../api/repair';
import { ingestProjectJson, triggerVerificationRun } from '../api/verification';
import {
  FailureAnalysisReport,
  RepairProposal,
  RepairVerificationComparison,
  RepairAuditLogEntry,
  RepairRuntimeStatus,
} from '../types/repair';

interface PresetScenario {
  id: string;
  name: string;
  description: string;
  files: Record<string, string>;
}

const PRESET_SCENARIOS: PresetScenario[] = [
  {
    id: 'operator-inversion',
    name: 'Arithmetic Operator Defect',
    description: 'calc.py returns a + b instead of a - b, failing test_subtract.',
    files: {
      'calc.py': 'def subtract(a, b):\n    # Implements REQ-001\n    return a + b\n',
      'tests/test_calc.py': 'from calc import subtract\n\ndef test_subtract():\n    # Verifies REQ-001\n    assert subtract(5, 3) == 2\n',
      'requirements.txt': 'pytest>=8.0.0\n',
    },
  },
  {
    id: 'boundary-inequality',
    name: 'Off-By-One Boundary Defect',
    description: 'validator.py checks age > 18 instead of age >= 18, failing boundary test.',
    files: {
      'validator.py': 'def check_age(age: int) -> bool:\n    # Implements REQ-002\n    return age > 18\n',
      'tests/test_validator.py': 'from validator import check_age\n\ndef test_boundary_age():\n    # Verifies REQ-002\n    assert check_age(18) is True\n',
      'requirements.txt': 'pytest>=8.0.0\n',
    },
  },
  {
    id: 'dictionary-key-crash',
    name: 'KeyError Unhandled Exception',
    description: 'cache.py uses direct bracket lookup instead of .get(key, None).',
    files: {
      'cache.py': 'class SafeCache:\n    def __init__(self):\n        self.cache = {}\n    def fetch(self, key):\n        return self.cache[key]\n',
      'tests/test_cache.py': 'from cache import SafeCache\n\ndef test_missing_key():\n    c = SafeCache()\n    assert c.fetch("missing") is None\n',
      'requirements.txt': 'pytest>=8.0.0\n',
    },
  },
];

export const RepairPage: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<PresetScenario>(PRESET_SCENARIOS[0]);
  const [runtimeStatus, setRuntimeStatus] = useState<RepairRuntimeStatus | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  // Failure analysis
  const [failures, setFailures] = useState<FailureAnalysisReport[]>([]);
  const [selectedFailure, setSelectedFailure] = useState<FailureAnalysisReport | null>(null);
  const [expandedTraceback, setExpandedTraceback] = useState<boolean>(true);

  // Proposals
  const [proposals, setProposals] = useState<RepairProposal[]>([]);
  const [selectedProposal, setSelectedProposal] = useState<RepairProposal | null>(null);
  const [comparison, setComparison] = useState<RepairVerificationComparison | null>(null);
  const [auditLogs, setAuditLogs] = useState<RepairAuditLogEntry[]>([]);

  // Generator settings & UI loading
  const [generatorType, setGeneratorType] = useState<string>('deterministic_rule_engine');
  const [rejectionReason, setRejectionReason] = useState<string>('');
  const [showRejectInput, setShowRejectInput] = useState<boolean>(false);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  useEffect(() => {
    fetchRuntimeStatus();
  }, []);

  const fetchRuntimeStatus = async () => {
    try {
      const status = await getRepairRuntimeStatus();
      setRuntimeStatus(status);
    } catch (e) {
      console.error('Failed to load repair runtime status', e);
    }
  };

  const handleIngestAndDiagnose = async () => {
    setLoadingAction('ingesting');
    setStatusMessage({ text: 'Ingesting scenario and executing baseline tests...', type: 'info' });
    try {
      const proj = await ingestProjectJson(selectedScenario.files, selectedScenario.name);
      setActiveProjectId(proj.project_id);

      const run = await triggerVerificationRun(proj.project_id);
      setActiveRunId(run.id);

      setStatusMessage({ text: `Test run finished (Status: ${run.status}). Analyzing failure patterns...`, type: 'info' });

      const analyzed = await analyzeRunFailures(run.id);
      setFailures(analyzed);
      if (analyzed.length > 0) {
        setSelectedFailure(analyzed[0]);
        setStatusMessage({ text: `Discovered ${analyzed.length} failure(s). Ready for repair generation.`, type: 'success' });
      } else {
        setSelectedFailure(null);
        setStatusMessage({ text: 'No test failures detected for this scenario.', type: 'info' });
      }

      // Refresh proposals & audit logs
      const pList = await listProposals(proj.project_id);
      setProposals(pList);
      if (pList.length > 0) {
        setSelectedProposal(pList[0]);
      } else {
        setSelectedProposal(null);
      }
      setComparison(null);
      const logs = await getRepairHistory();
      setAuditLogs(logs);
    } catch (err: any) {
      console.error(err);
      setStatusMessage({
        text: err?.response?.data?.detail || 'Error during ingestion and failure diagnosis.',
        type: 'error',
      });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGenerateProposal = async () => {
    if (!selectedFailure) return;
    setLoadingAction('generating');
    setStatusMessage({ text: 'Generating targeted repair candidate...', type: 'info' });
    try {
      const proposal = await generateProposal({
        failure_id: selectedFailure.failure_id,
        generator_override: generatorType,
      });
      setSelectedProposal(proposal);
      setProposals((prev) => [proposal, ...prev.filter((p) => p.repair_id !== proposal.repair_id)]);
      setStatusMessage({ text: `Repair proposal ${proposal.repair_id} created with ${proposal.generator_type}.`, type: 'success' });
      const logs = await getRepairHistory(proposal.repair_id);
      setAuditLogs(logs);
    } catch (err: any) {
      setStatusMessage({
        text: err?.response?.data?.detail || 'Failed to generate repair proposal.',
        type: 'error',
      });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleApprove = async () => {
    if (!selectedProposal) return;
    setLoadingAction('approving');
    try {
      const updated = await approveProposal(selectedProposal.repair_id);
      setSelectedProposal(updated);
      updateProposalInList(updated);
      setStatusMessage({ text: `Proposal ${updated.repair_id} explicitly APPROVED. Ready to apply to workspace.`, type: 'success' });
      refreshAudit(updated.repair_id);
    } catch (err: any) {
      setStatusMessage({ text: err?.response?.data?.detail || 'Failed to approve proposal.', type: 'error' });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleReject = async () => {
    if (!selectedProposal) return;
    setLoadingAction('rejecting');
    try {
      const updated = await rejectProposal(selectedProposal.repair_id, rejectionReason || undefined);
      setSelectedProposal(updated);
      updateProposalInList(updated);
      setShowRejectInput(false);
      setRejectionReason('');
      setStatusMessage({ text: `Proposal ${updated.repair_id} rejected.`, type: 'info' });
      refreshAudit(updated.repair_id);
    } catch (err: any) {
      setStatusMessage({ text: err?.response?.data?.detail || 'Failed to reject proposal.', type: 'error' });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleApply = async () => {
    if (!selectedProposal) return;
    setLoadingAction('applying');
    try {
      const res = await applyProposal(selectedProposal.repair_id);
      if (res.success) {
        const updated = { ...selectedProposal, status: 'applied' as const, patched_artifact_hash: res.new_sha256 };
        setSelectedProposal(updated);
        updateProposalInList(updated);
        setStatusMessage({ text: `Patch successfully applied to ${res.file_path}. Snapshot created. Ready for Docker verification.`, type: 'success' });
      }
      refreshAudit(selectedProposal.repair_id);
    } catch (err: any) {
      setStatusMessage({ text: err?.response?.data?.detail || 'Failed to apply patch.', type: 'error' });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleVerify = async () => {
    if (!selectedProposal) return;
    setLoadingAction('verifying');
    setStatusMessage({ text: 'Executing containerized tests to verify patch...', type: 'info' });
    try {
      const comp = await verifyProposal(selectedProposal.repair_id);
      setComparison(comp);
      const updated = { ...selectedProposal, status: comp.verification_status };
      setSelectedProposal(updated);
      updateProposalInList(updated);
      if (comp.verification_status === 'verified') {
        setStatusMessage({ text: 'Repair VERIFIED! All post-repair tests passed with zero regressions.', type: 'success' });
      } else {
        setStatusMessage({ text: 'Post-repair verification failed. Rollback available.', type: 'error' });
      }
      refreshAudit(selectedProposal.repair_id);
    } catch (err: any) {
      setStatusMessage({ text: err?.response?.data?.detail || 'Verification failed or Docker offline.', type: 'error' });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRollback = async () => {
    if (!selectedProposal) return;
    setLoadingAction('rolling_back');
    try {
      const res = await rollbackProposal(selectedProposal.repair_id);
      if (res.success) {
        const updated = { ...selectedProposal, status: 'rolled_back' as const };
        setSelectedProposal(updated);
        updateProposalInList(updated);
        setStatusMessage({ text: `Successfully rolled back ${selectedProposal.target_artifact_path} to pre-patch state.`, type: 'info' });
      }
      refreshAudit(selectedProposal.repair_id);
    } catch (err: any) {
      setStatusMessage({ text: err?.response?.data?.detail || 'Rollback failed.', type: 'error' });
    } finally {
      setLoadingAction(null);
    }
  };

  const updateProposalInList = (updated: RepairProposal) => {
    setProposals((prev) => prev.map((p) => (p.repair_id === updated.repair_id ? updated : p)));
  };

  const refreshAudit = async (repairId?: string) => {
    try {
      const logs = await getRepairHistory(repairId);
      setAuditLogs(logs);
    } catch (e) {
      console.error(e);
    }
  };

  const renderStatusBadge = (status: string) => {
    const badgeColors: Record<string, string> = {
      proposed: 'bg-amber-900/40 text-amber-300 border-amber-700/50',
      approved: 'bg-blue-900/40 text-blue-300 border-blue-700/50',
      rejected: 'bg-red-900/40 text-red-300 border-red-700/50',
      applied: 'bg-indigo-900/40 text-indigo-300 border-indigo-700/50',
      verified: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/50',
      failed_verification: 'bg-rose-900/40 text-rose-300 border-rose-700/50',
      rolled_back: 'bg-slate-800 text-slate-300 border-slate-700',
      blocked: 'bg-orange-900/40 text-orange-300 border-orange-700/50',
    };
    return (
      <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wider ${badgeColors[status] || 'bg-slate-800 text-slate-300'}`}>
        {status.replace('_', ' ')}
      </span>
    );
  };

  const renderRiskBadge = (risk: string) => {
    const riskColors: Record<string, string> = {
      low: 'text-emerald-400 bg-emerald-950/40 border-emerald-800',
      medium: 'text-amber-400 bg-amber-950/40 border-amber-800',
      high: 'text-rose-400 bg-rose-950/40 border-rose-800',
      security_restricted: 'text-purple-400 bg-purple-950/40 border-purple-800',
    };
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${riskColors[risk] || 'text-slate-400'}`}>
        Risk: {risk.replace('_', ' ')}
      </span>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Wrench className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Failure-Guided Automated Code Repair</h1>
              <p className="text-sm text-slate-400">
                Deterministic bug fixing, AST validation, rollback snapshots, and isolated container verification
              </p>
            </div>
          </div>
        </div>

        {/* Runtime Diagnostics Status Bar */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-slate-400">Rule Engine:</span>
            <span className="text-emerald-400 font-medium">Deterministic</span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Model:</span>
            <span className={runtimeStatus?.local_code_model === 'ready' ? 'text-emerald-400 font-medium' : 'text-slate-400'}>
              {runtimeStatus?.local_code_model === 'ready' ? runtimeStatus.code_model_name : 'Ollama Offline'}
            </span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            <Terminal className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Sandbox:</span>
            <span className={runtimeStatus?.docker_sandbox === 'ready' ? 'text-emerald-400 font-medium' : 'text-amber-400'}>
              {runtimeStatus?.docker_sandbox === 'ready' ? 'Docker Ready' : 'Host Guarded'}
            </span>
          </div>

          <button
            onClick={fetchRuntimeStatus}
            className="p-1.5 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition"
            title="Refresh runtime status"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Status Alert Banner */}
      {statusMessage && (
        <div
          className={`px-4 py-3 rounded-lg border text-sm flex items-center justify-between ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
              : statusMessage.type === 'error'
              ? 'bg-rose-950/40 border-rose-800 text-rose-300'
              : 'bg-blue-950/40 border-blue-800 text-blue-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {statusMessage.type === 'success' && <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />}
            {statusMessage.type === 'error' && <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />}
            {statusMessage.type === 'info' && <Layers className="w-4 h-4 text-blue-400 shrink-0" />}
            <span>{statusMessage.text}</span>
          </div>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Section 1: Scenario Ingestion & Diagnosis */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Play className="w-4 h-4 text-emerald-400" />
              1. Load Defect Scenario & Run Diagnosis
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Select a reproducible defect scenario to ingest into the isolated project workspace and run tests.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={selectedScenario.id}
              onChange={(e) => {
                const s = PRESET_SCENARIOS.find((sc) => sc.id === e.target.value);
                if (s) setSelectedScenario(s);
              }}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              {PRESET_SCENARIOS.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  {sc.name}
                </option>
              ))}
            </select>

            <button
              onClick={handleIngestAndDiagnose}
              disabled={loadingAction === 'ingesting'}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition flex items-center gap-2 disabled:opacity-50"
            >
              {loadingAction === 'ingesting' ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Ingesting...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" /> Ingest & Diagnose
                </>
              )}
            </button>
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs text-slate-400 bg-slate-950/50 p-2.5 rounded border border-slate-800/80">
          <div>
            <span className="font-semibold text-slate-300">Scenario Description: </span>
            {selectedScenario.description}
          </div>
          {activeProjectId && (
            <div className="flex items-center gap-2 font-mono text-[11px] text-slate-500">
              <span>Proj: {activeProjectId}</span>
              {activeRunId && <span>| Run: {activeRunId}</span>}
            </div>
          )}
        </div>
      </div>

      {/* Grid: Left Column (Failures & Hypotheses) | Right Column (Proposal Studio & Unified Diff) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Failure Reports */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                2. Diagnosed Failures ({failures.length})
              </h2>
            </div>

            {failures.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">
                No active failures diagnosed. Click &ldquo;Ingest & Diagnose&rdquo; above to load a failing scenario.
              </div>
            ) : (
              <div className="space-y-3">
                {failures.map((f) => (
                  <div
                    key={f.failure_id}
                    onClick={() => setSelectedFailure(f)}
                    className={`p-3.5 rounded-lg border cursor-pointer transition ${
                      selectedFailure?.failure_id === f.failure_id
                        ? 'bg-slate-800/90 border-emerald-500/60 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-medium text-emerald-400">{f.failure_id}</span>
                          <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                            {f.category}
                          </span>
                        </div>
                        <p className="text-sm font-medium text-slate-200 mt-1 line-clamp-1">{f.test_id}</p>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-800/40">
                        {f.classification}
                      </span>
                    </div>

                    {f.suspected_file && (
                      <div className="mt-2 text-xs text-slate-400 flex items-center gap-1.5 font-mono">
                        <FileCode className="w-3.5 h-3.5 text-slate-500" />
                        <span>
                          {f.suspected_file}
                          {f.suspected_line ? `:${f.suspected_line}` : ''}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Selected Failure Details & Hypotheses */}
          {selectedFailure && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                Ranked Root-Cause Hypotheses
              </h3>

              {selectedFailure.hypotheses.map((h) => (
                <div key={h.rank} className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                      Rank #{h.rank}
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      Confidence: {(h.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">{h.description}</p>
                  <p className="text-[11px] text-slate-500 font-mono line-clamp-2">Evidence: {h.evidence_basis}</p>
                </div>
              ))}

              {/* Traceback Accordion */}
              <div className="border border-slate-800 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedTraceback(!expandedTraceback)}
                  className="w-full flex items-center justify-between px-3 py-2 bg-slate-950 text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  <span className="flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-slate-500" /> Traceback Excerpt
                  </span>
                  {expandedTraceback ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
                {expandedTraceback && (
                  <pre className="p-3 bg-black/60 text-[11px] text-slate-300 font-mono overflow-x-auto max-h-52 leading-tight">
                    {selectedFailure.traceback_excerpt}
                  </pre>
                )}
              </div>

              {/* Generator Trigger Button */}
              <div className="pt-2 border-t border-slate-800 flex items-center gap-3">
                <select
                  value={generatorType}
                  onChange={(e) => setGeneratorType(e.target.value)}
                  className="bg-slate-950 border border-slate-700 text-xs text-slate-300 rounded px-2.5 py-2 flex-1"
                >
                  <option value="deterministic_rule_engine">Deterministic Rule Engine (Fast / Safe)</option>
                  <option value="local_code_model">Local Code Model (Qwen2.5-Coder)</option>
                </select>

                <button
                  onClick={handleGenerateProposal}
                  disabled={loadingAction === 'generating'}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition disabled:opacity-50"
                >
                  {loadingAction === 'generating' ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5" />
                  )}
                  Synthesize Patch
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Repair Studio, Unified Diff, Lifecycle & Audit */}
        <div className="lg:col-span-7 space-y-5">
          {/* Proposal Header & Details */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div>
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <FileDiff className="w-4 h-4 text-emerald-400" />
                  3. Repair Proposal Studio {proposals.length > 0 && `(${proposals.length})`}
                </h2>
                {selectedProposal && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    Candidate: <span className="text-slate-200 font-mono">{selectedProposal.repair_id}</span> ({selectedProposal.target_artifact_path})
                  </p>
                )}
              </div>

              {selectedProposal && (
                <div className="flex items-center gap-2">
                  {renderStatusBadge(selectedProposal.status)}
                  {renderRiskBadge(selectedProposal.risk_level)}
                </div>
              )}
            </div>

            {!selectedProposal ? (
              <div className="text-center py-12 text-slate-500 text-sm">
                No proposal selected or generated yet. Select a failure on the left and click &ldquo;Synthesize Patch&rdquo;.
              </div>
            ) : (
              <div className="space-y-4">
                {/* Explanation */}
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs text-slate-300 leading-relaxed">
                  <span className="font-semibold text-slate-200">Rationale: </span>
                  {selectedProposal.explanation}
                </div>

                {/* Unified Diff View */}
                <div className="border border-slate-800 rounded-lg overflow-hidden">
                  <div className="px-3 py-2 bg-slate-950 border-b border-slate-800 text-xs font-mono text-slate-400 flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <FileCode className="w-3.5 h-3.5 text-slate-500" /> {selectedProposal.target_artifact_path}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      SHA: {selectedProposal.original_artifact_hash.slice(0, 10)}...
                    </span>
                  </div>

                  <pre className="p-3 bg-black/80 font-mono text-xs overflow-x-auto max-h-72 leading-relaxed">
                    {selectedProposal.unified_diff.split('\n').map((line, idx) => {
                      let lineClass = 'text-slate-400';
                      if (line.startsWith('+') && !line.startsWith('+++')) {
                        lineClass = 'text-emerald-400 bg-emerald-950/40 px-1 rounded-sm';
                      } else if (line.startsWith('-') && !line.startsWith('---')) {
                        lineClass = 'text-rose-400 bg-rose-950/40 px-1 rounded-sm';
                      } else if (line.startsWith('@@')) {
                        lineClass = 'text-blue-400 font-bold';
                      }
                      return (
                        <div key={idx} className={lineClass}>
                          {line}
                        </div>
                      );
                    })}
                  </pre>
                </div>

                {/* Lifecycle Action Buttons */}
                <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center gap-3">
                  {/* Approve */}
                  {selectedProposal.status === 'proposed' && (
                    <button
                      onClick={handleApprove}
                      disabled={loadingAction === 'approving'}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition disabled:opacity-50"
                    >
                      <Check className="w-3.5 h-3.5" /> Approve Proposal
                    </button>
                  )}

                  {/* Reject */}
                  {selectedProposal.status === 'proposed' && !showRejectInput && (
                    <button
                      onClick={() => setShowRejectInput(true)}
                      className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg flex items-center gap-1.5 transition"
                    >
                      <X className="w-3.5 h-3.5" /> Reject
                    </button>
                  )}

                  {/* Rejection input */}
                  {showRejectInput && (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder="Rejection reason..."
                        value={rejectionReason}
                        onChange={(e) => setRejectionReason(e.target.value)}
                        className="bg-slate-950 border border-slate-700 text-xs text-slate-200 px-2.5 py-1.5 rounded"
                      />
                      <button
                        onClick={handleReject}
                        disabled={loadingAction === 'rejecting'}
                        className="px-2.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium rounded"
                      >
                        Confirm Reject
                      </button>
                      <button
                        onClick={() => setShowRejectInput(false)}
                        className="px-2.5 py-1.5 bg-slate-800 text-slate-400 text-xs font-medium rounded"
                      >
                        Cancel
                      </button>
                    </div>
                  )}

                  {/* Apply Patch */}
                  {selectedProposal.status === 'approved' && (
                    <button
                      onClick={handleApply}
                      disabled={loadingAction === 'applying'}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition disabled:opacity-50"
                    >
                      <GitCommit className="w-3.5 h-3.5" /> Apply Patch to Workspace
                    </button>
                  )}

                  {/* Verify in Docker */}
                  {selectedProposal.status === 'applied' && (
                    <button
                      onClick={handleVerify}
                      disabled={loadingAction === 'verifying'}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition disabled:opacity-50"
                    >
                      <Play className="w-3.5 h-3.5" /> Verify in Docker Sandbox
                    </button>
                  )}

                  {/* Rollback */}
                  {(selectedProposal.status === 'applied' ||
                    selectedProposal.status === 'verified' ||
                    selectedProposal.status === 'failed_verification') && (
                    <button
                      onClick={handleRollback}
                      disabled={loadingAction === 'rolling_back'}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition disabled:opacity-50 ml-auto"
                    >
                      <RotateCcw className="w-3.5 h-3.5 text-slate-400" /> Rollback to Snapshot
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Verification Comparison (Before & After) */}
          {comparison && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Before & After Test Verification Audit
              </h3>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <div className="text-xs text-slate-400">Pre-Repair Failures</div>
                  <div className="text-2xl font-bold text-rose-400 mt-1">{comparison.pre_failures_count}</div>
                  <div className="text-[11px] text-slate-500 font-mono mt-0.5">Run: {comparison.pre_run_id}</div>
                </div>

                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <div className="text-xs text-slate-400">Post-Repair Failures</div>
                  <div className={`text-2xl font-bold mt-1 ${comparison.post_failures_count === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {comparison.post_failures_count}
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono mt-0.5">Run: {comparison.post_run_id}</div>
                </div>
              </div>

              {comparison.fixed_test_ids.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5" /> Fixed Tests
                  </div>
                  {comparison.fixed_test_ids.map((t, idx) => (
                    <div key={idx} className="p-2 bg-emerald-950/30 border border-emerald-800/40 rounded text-xs font-mono text-emerald-300">
                      {t}
                    </div>
                  ))}
                </div>
              )}

              <p className="text-xs text-slate-400 bg-slate-950/60 p-2.5 rounded border border-slate-800">
                <span className="font-semibold text-slate-300">Rationale: </span>
                {comparison.rationale}
              </p>
            </div>
          )}

          {/* Immutable Audit Trail Ledger */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <History className="w-4 h-4 text-slate-400" />
              Immutable Repair Audit Ledger
            </h3>

            {auditLogs.length === 0 ? (
              <div className="text-center py-4 text-slate-500 text-xs">No audit events recorded yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="pb-2">Action</th>
                      <th className="pb-2">Transition</th>
                      <th className="pb-2">Actor</th>
                      <th className="pb-2">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {auditLogs.slice(0, 8).map((log) => (
                      <tr key={log.id} className="text-slate-300 hover:bg-slate-950/40">
                        <td className="py-2 text-emerald-400 font-semibold">{log.action}</td>
                        <td className="py-2 text-slate-400">
                          {log.from_status} <span className="text-slate-600">→</span> {log.to_status}
                        </td>
                        <td className="py-2 text-slate-400">{log.actor}</td>
                        <td className="py-2 text-slate-500 text-[11px]">{new Date(log.timestamp).toLocaleTimeString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RepairPage;
