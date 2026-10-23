import { apiClient } from "./client";
import {
  ChangeImpactReport,
  HistoricalObservationItem,
  ModelStatusReport,
  PrioritizationReport,
  PrioritizationStrategy,
  TestSelectionReport,
} from "../types/regression";

export async function analyzeChangeImpact(
  projectId: string,
  changedFiles: string[],
  fileContents?: Record<string, string>,
  diffText?: string
): Promise<ChangeImpactReport> {
  const response = await apiClient.post<ChangeImpactReport>("/regression/analyze", {
    project_id: projectId,
    changed_files: changedFiles,
    file_contents: fileContents || null,
    diff_text: diffText || null,
  });
  return response.data;
}

export async function prioritizeTests(
  projectId: string,
  changedFiles: string[],
  strategy: PrioritizationStrategy = "predictive",
  topK?: number,
  executionBudgetMs?: number
): Promise<PrioritizationReport> {
  const response = await apiClient.post<PrioritizationReport>("/regression/prioritize", {
    project_id: projectId,
    changed_files: changedFiles,
    strategy,
    top_k: topK || null,
    execution_budget_ms: executionBudgetMs || null,
  });
  return response.data;
}

export async function selectTests(
  projectId: string,
  changedFiles: string[],
  strategy: PrioritizationStrategy = "predictive",
  topK?: number,
  executionBudgetMs?: number
): Promise<TestSelectionReport> {
  const response = await apiClient.post<TestSelectionReport>("/regression/select", {
    project_id: projectId,
    changed_files: changedFiles,
    strategy,
    top_k: topK || null,
    execution_budget_ms: executionBudgetMs || null,
  });
  return response.data;
}

export async function getAnalysis(analysisId: string): Promise<ChangeImpactReport> {
  const response = await apiClient.get<ChangeImpactReport>(`/regression/analyses/${analysisId}`);
  return response.data;
}

export async function getModelStatus(): Promise<ModelStatusReport> {
  const response = await apiClient.get<ModelStatusReport>("/regression/model/status");
  return response.data;
}

export async function trainModel(
  includeSynthetic: boolean = false,
  algorithm: string = "RandomForestClassifier"
): Promise<any> {
  const response = await apiClient.post("/regression/model/train", {
    include_synthetic: includeSynthetic,
    algorithm,
  });
  return response.data;
}

export async function evaluateModel(
  includeSynthetic: boolean = false,
  topK: number = 3
): Promise<any> {
  const response = await apiClient.post("/regression/model/evaluate", {
    include_synthetic: includeSynthetic,
    top_k: topK,
  });
  return response.data;
}

export async function getHistory(
  projectId?: string,
  includeSynthetic: boolean = false
): Promise<HistoricalObservationItem[]> {
  const params: Record<string, any> = { include_synthetic: includeSynthetic };
  if (projectId) params.project_id = projectId;
  const response = await apiClient.get<HistoricalObservationItem[]>("/regression/history", { params });
  return response.data;
}
