export type ComponentStatus = "ready" | "unavailable" | "not_configured" | "not_trained";

export interface ComponentDiagnostic {
  status: ComponentStatus;
  message: string;
  details?: Record<string, unknown>;
  troubleshooting?: string;
  latency_ms?: number;
}

export interface SystemStatusResponse {
  overall_status: "ready" | "degraded" | "setup_required" | string;
  version: string;
  environment: string;
  timestamp: string;
  components: {
    database: ComponentDiagnostic;
    ai_runtime: ComponentDiagnostic;
    model_artifacts: ComponentDiagnostic;
    sandbox: ComponentDiagnostic;
    [key: string]: ComponentDiagnostic;
  };
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
}
