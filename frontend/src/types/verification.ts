export type FileType =
  | "source_file"
  | "test_file"
  | "manifest"
  | "config"
  | "documentation"
  | "other";

export type LinkType =
  | "candidate_implementation"
  | "confirmed_implementation"
  | "candidate_test"
  | "confirmed_test";

export type LinkOrigin =
  | "static_analysis"
  | "heuristic_inference"
  | "developer_confirmation";

export type ExecutionStatus =
  | "queued"
  | "running"
  | "passed"
  | "failed"
  | "timed_out"
  | "unavailable"
  | "error";

export type RequirementVerdictStatus = "verified" | "failed" | "unverified";

export interface ArtifactMetadata {
  id: string;
  project_id: string;
  relative_path: string;
  file_type: FileType;
  language: string;
  sha256: string;
  size_bytes: number;
  line_count: number;
  symbols: string[];
  created_at: string;
}

export interface ProjectIngestionReport {
  project_id: string;
  name: string;
  total_files: number;
  total_size_bytes: number;
  detected_manifests: string[];
  detected_test_frameworks: string[];
  available_test_commands: string[];
  ingested_artifacts: ArtifactMetadata[];
  warnings: string[];
  ingested_at: string;
}

export interface TraceabilityLink {
  id: string;
  project_id: string;
  specification_id: string;
  requirement_id: string;
  artifact_path: string;
  symbol_name?: string;
  line_start?: number;
  line_end?: number;
  link_type: LinkType;
  link_origin: LinkOrigin;
  confidence: number;
  is_confirmed: boolean;
  rationale: string;
  created_at: string;
  confirmed_at?: string;
}

export interface RequirementEvidenceVerdict {
  requirement_id: string;
  requirement_title: string;
  verdict: RequirementVerdictStatus;
  linked_code_count: number;
  linked_test_count: number;
  passed_tests: string[];
  failed_tests: string[];
  rationale: string;
}

export interface VerificationRun {
  id: string;
  project_id: string;
  specification_id?: string;
  status: ExecutionStatus;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  duration_ms: number;
  stdout: string;
  stderr: string;
  exit_code?: number;
  static_analysis_passed: boolean;
  static_findings: string[];
  requirement_verdicts: Record<string, RequirementEvidenceVerdict>;
  docker_available: boolean;
  created_at: string;
  completed_at?: string;
}

export interface RequirementEvidenceReport {
  specification_id: string;
  project_id?: string;
  total_requirements: number;
  candidate_code_linked_count: number;
  confirmed_code_linked_count: number;
  linked_test_count: number;
  verified_requirement_count: number;
  failed_requirement_count: number;
  unverified_requirement_count: number;
  verification_coverage_pct: number;
  verdicts: RequirementEvidenceVerdict[];
  latest_run_id?: string;
  latest_run_status?: ExecutionStatus;
  notes: string[];
}

export interface ProjectSummary {
  project_id: string;
  name: string;
  total_files: number;
  ingested_at: string;
}

export interface DockerStatusResponse {
  docker_available: boolean;
  message: string;
  fail_closed_policy: string;
}
