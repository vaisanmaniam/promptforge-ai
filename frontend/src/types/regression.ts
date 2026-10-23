export type ChangeType = "added" | "modified" | "deleted";

export type PrioritizationStrategy = "all_tests" | "impact_based" | "predictive";

export interface ChangedFileInfo {
  file_path: string;
  change_type: ChangeType;
  changed_symbols: string[];
  is_test: boolean;
}

export interface AffectedRequirementInfo {
  requirement_id: string;
  title: string;
  priority: string;
  is_directly_changed: boolean;
  impact_distance: number;
  linked_code_artifacts: string[];
}

export interface ChangeImpactReport {
  analysis_id: string;
  project_id: string;
  changed_files: ChangedFileInfo[];
  changed_symbols: string[];
  directly_affected_requirements: AffectedRequirementInfo[];
  downstream_affected_requirements: AffectedRequirementInfo[];
  max_blast_radius_depth: number;
  affected_tests_candidate_count: number;
  evidence_disclosures: string[];
  created_at: string;
}

export interface RankedTestItem {
  rank: number;
  test_id: string;
  file_path: string;
  symbol_name?: string;
  score: number;
  predicted_failure_probability?: number;
  confidence: number;
  explanations: string[];
  is_directly_affected: boolean;
  verifies_requirement_id?: string;
  historical_failure_rate?: number;
  historical_duration_ms?: number;
  method: string;
  is_selected: boolean;
}

export interface ExcludedTestItem {
  test_id: string;
  rank: number;
  score: number;
  exclusion_reason: string;
}

export interface PrioritizationReport {
  analysis_id: string;
  project_id: string;
  strategy_used: PrioritizationStrategy;
  fallback_to_baseline: boolean;
  fallback_reason?: string;
  model_status: string;
  total_tests_discovered: number;
  ranked_tests: RankedTestItem[];
  created_at: string;
}

export interface TestSelectionReport {
  analysis_id: string;
  project_id: string;
  strategy: PrioritizationStrategy;
  total_tests: number;
  selected_count: number;
  excluded_count: number;
  selected_tests: RankedTestItem[];
  excluded_tests: ExcludedTestItem[];
  estimated_duration_ms: number;
  fallback_to_baseline: boolean;
  fallback_reason?: string;
  created_at: string;
}

export interface ModelStatusReport {
  model_name: string;
  status: "trained" | "not_trained";
  is_trained: boolean;
  version: string;
  resolved_path: string;
  training_sample_count: number;
  fallback_behavior: string;
  notes: string;
  evaluation_metrics?: Record<string, any>;
}

export interface HistoricalObservationItem {
  observation_id: string;
  change_id: string;
  project_id: string;
  test_id: string;
  outcome: number;
  label_provenance: string;
  is_synthetic: boolean;
  timestamp: string;
}
