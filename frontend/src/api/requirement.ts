import { apiClient } from "./client";
import {
  CoverageReport,
  ExtractRequirementsResponse,
  ImpactAnalysisReport,
  RequirementSpecification,
  SpecificationListResponse,
  TraceabilityGraph,
  ValidationReport,
} from "../types/requirement";

export async function extractRequirements(
  prompt: string,
  taskCategory?: string
): Promise<ExtractRequirementsResponse> {
  const response = await apiClient.post<ExtractRequirementsResponse>(
    "/requirements/extract",
    {
      prompt,
      task_category: taskCategory || null,
    }
  );
  return response.data;
}

export async function createSpecification(
  prompt: string,
  title?: string,
  taskCategory?: string
): Promise<RequirementSpecification> {
  const response = await apiClient.post<RequirementSpecification>(
    "/requirements/specifications",
    {
      prompt,
      title: title || null,
      task_category: taskCategory || null,
    }
  );
  return response.data;
}

export async function listSpecifications(): Promise<SpecificationListResponse> {
  const response = await apiClient.get<SpecificationListResponse>(
    "/requirements/specifications"
  );
  return response.data;
}

export async function getSpecification(
  specId: string
): Promise<RequirementSpecification> {
  const response = await apiClient.get<RequirementSpecification>(
    `/requirements/specifications/${specId}`
  );
  return response.data;
}

export async function getTraceabilityGraph(
  specId: string
): Promise<TraceabilityGraph> {
  const response = await apiClient.get<TraceabilityGraph>(
    `/requirements/specifications/${specId}/graph`
  );
  return response.data;
}

export async function getImpactAnalysis(
  specId: string,
  reqId: string
): Promise<ImpactAnalysisReport> {
  const response = await apiClient.get<ImpactAnalysisReport>(
    `/requirements/specifications/${specId}/impact/${reqId}`
  );
  return response.data;
}

export async function getCoverageReport(
  specId: string
): Promise<CoverageReport> {
  const response = await apiClient.get<CoverageReport>(
    `/requirements/specifications/${specId}/coverage`
  );
  return response.data;
}

export async function getValidationReport(
  specId: string
): Promise<ValidationReport> {
  const response = await apiClient.get<ValidationReport>(
    `/requirements/specifications/${specId}/validation`
  );
  return response.data;
}
