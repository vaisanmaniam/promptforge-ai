export type TaskCategory =
  | "code_generation"
  | "debugging"
  | "code_review"
  | "api_development"
  | "sql_generation"
  | "test_generation"
  | "documentation"
  | "devops";

export interface ClassificationResult {
  predicted_category: TaskCategory | string;
  confidence: number;
  probabilities: Record<string, number>;
  model_name: string;
  model_version: string;
  method: string;
  is_baseline: boolean;
}

export interface ComponentFinding {
  component: string;
  status: "detected" | "missing" | "uncertain";
  evidence?: string;
  confidence: number;
  detection_method: string;
}

export interface ComponentDetectionReport {
  detected: string[];
  missing: string[];
  uncertain: string[];
  findings: Record<string, ComponentFinding>;
}

export interface AmbiguityFinding {
  term: string;
  category: string;
  explanation: string;
  clarification_question: string;
}

export interface AmbiguityReport {
  has_ambiguity: boolean;
  findings: AmbiguityFinding[];
  ambiguity_count: number;
}

export interface DimensionScore {
  dimension: string;
  weight: number;
  score: number;
  weighted_score: number;
  explanation: string;
}

export interface QualityAssessment {
  overall_score: number;
  dimension_scores: Record<string, DimensionScore>;
  positive_evidence: string[];
  missing_information: string[];
  recommendations: string[];
  scoring_version: string;
  method: string;
}

export interface TokenAnalysisReport {
  original_tokens: number;
  optimized_tokens: number;
  token_delta: number;
  percentage_change: number;
  original_quality_per_token: number;
  optimized_quality_per_token: number;
  counting_method: string;
  tokenizer_identity: string;
  is_exact: boolean;
}

export interface PromptOptimizationResult {
  original_prompt: string;
  optimized_prompt: string;
  task_category: string;
  added_sections: string[];
  assumptions: string[];
  clarification_questions: string[];
  explanation_of_changes: string[];
}

export interface AnalyzePromptRequest {
  prompt: string;
  task_category?: string | null;
}

export interface AnalyzePromptResponse {
  task_classification: ClassificationResult;
  components: ComponentDetectionReport;
  ambiguity: AmbiguityReport;
  quality: QualityAssessment;
  token_count: number;
  token_counting_method: string;
  tokenizer_identity: string;
  is_exact_tokens: boolean;
}

export interface OptimizePromptRequest {
  prompt: string;
  task_category?: string | null;
}

export interface OptimizePromptResponse {
  optimization: PromptOptimizationResult;
  task_classification: ClassificationResult;
  original_quality: QualityAssessment;
  optimized_quality: QualityAssessment;
  token_analysis: TokenAnalysisReport;
}
