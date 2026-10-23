export type RequirementCategory = "functional" | "nonfunctional" | "technical_constraint" | "security";

export type RequirementPriority = "critical" | "high" | "medium" | "low";

export type RequirementStatus = "explicit" | "inferred";

export type VerificationState = "unverified" | "verified" | "failed";

export type AssumptionStatus = "unresolved" | "confirmed" | "rejected";

export interface AcceptanceCriterion {
  id: string;
  description: string;
  verification_type: string;
  status: string;
}

export interface AssumptionItem {
  id: string;
  text: string;
  source_component: string;
  status: AssumptionStatus;
  impact: string;
}

export interface RequirementItem {
  id: string;
  title: string;
  description: string;
  category: RequirementCategory;
  priority: RequirementPriority;
  status: RequirementStatus;
  source_text?: string;
  assumptions: AssumptionItem[];
  acceptance_criteria: AcceptanceCriterion[];
  verification_state: VerificationState;
  depends_on: string[];
  refines: string[];
}

export interface RequirementSpecification {
  id: string;
  title: string;
  source_prompt: string;
  task_category?: string;
  category_breakdown: Record<string, number>;
  requirements: RequirementItem[];
  assumptions: AssumptionItem[];
  created_at: string;
  updated_at: string;
  version: number;
}

export interface ValidationFinding {
  rule_id: string;
  severity: "error" | "warning" | "info";
  target_req_id?: string;
  message: string;
  suggestion: string;
}

export interface ValidationReport {
  total_findings: number;
  errors: number;
  warnings: number;
  info: number;
  findings: ValidationFinding[];
  is_valid: boolean;
}

export interface TraceabilityNode {
  id: string;
  type: string;
  label: string;
  category?: string;
  status?: string;
  priority?: string;
  metadata?: Record<string, unknown>;
}

export interface TraceabilityEdge {
  source: string;
  target: string;
  relation: string;
}

export interface TraceabilityGraph {
  nodes: TraceabilityNode[];
  edges: TraceabilityEdge[];
  has_cycles: boolean;
  cycle_paths: string[][];
  isolated_nodes: string[];
}

export interface ImpactAnalysisReport {
  target_req_id: string;
  upstream_dependencies: string[];
  downstream_dependents: string[];
  impact_depth: number;
  risk_level: "low" | "medium" | "high" | "critical";
}

export interface CoverageReport {
  total_requirements: number;
  explicit_count: number;
  inferred_count: number;
  prompt_coverage_pct: number;
  acceptance_criteria_coverage_pct: number;
  assumption_resolution_pct: number;
  category_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  code_traceability_status: string;
  test_traceability_status: string;
  summary_notes: string[];
}

export interface ExtractRequirementsResponse {
  specification: RequirementSpecification;
  validation: ValidationReport;
  coverage: CoverageReport;
}

export interface SpecificationSummary {
  id: string;
  title: string;
  task_category?: string;
  total_requirements: number;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface SpecificationListResponse {
  specifications: SpecificationSummary[];
  total: number;
}
