export type FailureCategory =
  | 'assertion_failure'
  | 'exception'
  | 'syntax_error'
  | 'import_error'
  | 'static_analysis_violation'
  | 'timeout'
  | 'environment_blocked'
  | 'unknown';

export type DefectClassification =
  | 'code_defect'
  | 'test_defect'
  | 'environment_issue'
  | 'unresolved';

export type RepairCandidateStatus =
  | 'proposed'
  | 'approved'
  | 'rejected'
  | 'applied'
  | 'verified'
  | 'failed_verification'
  | 'rolled_back'
  | 'stale'
  | 'blocked';

export type RiskLevel =
  | 'low'
  | 'medium'
  | 'high'
  | 'security_restricted';

export interface FailureHypothesis {
  rank: number;
  description: string;
  confidence: number;
  evidence_basis: string;
  suspected_file?: string | null;
  suspected_line?: number | null;
}

export interface FailureAnalysisReport {
  failure_id: string;
  run_id: string;
  project_id: string;
  test_id: string;
  category: FailureCategory;
  classification: DefectClassification;
  traceback_excerpt: string;
  suspected_file?: string | null;
  suspected_line?: number | null;
  related_requirement_ids: string[];
  hypotheses: FailureHypothesis[];
  created_at: string;
}

export interface RepairProposal {
  repair_id: string;
  failure_ids: string[];
  project_id: string;
  target_artifact_path: string;
  original_artifact_hash: string;
  patched_artifact_hash?: string | null;
  original_content?: string | null;
  patched_content: string;
  unified_diff: string;
  explanation: string;
  status: RepairCandidateStatus;
  risk_level: RiskLevel;
  generator_type: string;
  related_requirement_ids: string[];
  related_test_ids: string[];
  created_at: string;
  approved_at?: string | null;
  applied_at?: string | null;
  verified_at?: string | null;
  rejection_reason?: string | null;
}

export interface PatchApplicationResult {
  success: boolean;
  repair_id: string;
  file_path: string;
  original_sha256: string;
  new_sha256: string;
  rollback_available: boolean;
  message: string;
}

export interface RepairVerificationComparison {
  repair_id: string;
  pre_run_id: string;
  post_run_id: string;
  pre_failures_count: number;
  post_failures_count: number;
  fixed_test_ids: string[];
  new_failure_test_ids: string[];
  verification_status: RepairCandidateStatus;
  rationale: string;
}

export interface RepairAuditLogEntry {
  id: string;
  repair_id: string;
  action: string;
  actor: string;
  from_status: string;
  to_status: string;
  timestamp: string;
  details: Record<string, any>;
}

export interface RepairRuntimeStatus {
  deterministic_engine: boolean;
  local_code_model: string;
  code_model_name: string;
  docker_sandbox: string;
  details?: Record<string, any>;
}

export interface GenerateProposalRequest {
  failure_id: string;
  generator_override?: string | null;
}

export interface ProposalDecisionRequest {
  decision_reason?: string | null;
}
