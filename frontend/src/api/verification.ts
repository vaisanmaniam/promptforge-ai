import { apiClient } from "./client";
import {
  ArtifactMetadata,
  DockerStatusResponse,
  ProjectIngestionReport,
  ProjectSummary,
  RequirementEvidenceReport,
  TraceabilityLink,
  VerificationRun,
} from "../types/verification";

export async function ingestProjectArchive(
  file: File,
  projectName?: string
): Promise<ProjectIngestionReport> {
  const formData = new FormData();
  formData.append("file", file);
  if (projectName) {
    formData.append("project_name", projectName);
  }

  const response = await apiClient.post<ProjectIngestionReport>(
    "/verification/projects",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return response.data;
}

export async function ingestProjectJson(
  files: Record<string, string>,
  projectName?: string
): Promise<ProjectIngestionReport> {
  const response = await apiClient.post<ProjectIngestionReport>(
    "/verification/projects/json",
    {
      name: projectName || null,
      files,
    }
  );
  return response.data;
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const response = await apiClient.get<ProjectSummary[]>("/verification/projects");
  return response.data;
}

export async function getProject(
  projectId: string
): Promise<ProjectIngestionReport> {
  const response = await apiClient.get<ProjectIngestionReport>(
    `/verification/projects/${projectId}`
  );
  return response.data;
}

export async function getProjectArtifacts(
  projectId: string
): Promise<ArtifactMetadata[]> {
  const response = await apiClient.get<ArtifactMetadata[]>(
    `/verification/projects/${projectId}/artifacts`
  );
  return response.data;
}

export async function linkRequirements(
  projectId: string,
  specificationId: string
): Promise<TraceabilityLink[]> {
  const response = await apiClient.post<TraceabilityLink[]>(
    `/verification/projects/${projectId}/link-requirements`,
    { specification_id: specificationId }
  );
  return response.data;
}

export async function getProjectTraceability(
  projectId: string
): Promise<TraceabilityLink[]> {
  const response = await apiClient.get<TraceabilityLink[]>(
    `/verification/projects/${projectId}/traceability`
  );
  return response.data;
}

export async function confirmLink(
  projectId: string,
  linkId: string,
  isConfirmed: boolean
): Promise<TraceabilityLink> {
  const response = await apiClient.post<TraceabilityLink>(
    `/verification/projects/${projectId}/confirm-link/${linkId}`,
    { is_confirmed: isConfirmed }
  );
  return response.data;
}

export async function triggerVerificationRun(
  projectId: string,
  specificationId?: string,
  testCommand?: string[]
): Promise<VerificationRun> {
  const response = await apiClient.post<VerificationRun>(
    `/verification/projects/${projectId}/runs`,
    {
      specification_id: specificationId || null,
      test_command: testCommand || null,
    }
  );
  return response.data;
}

export async function getVerificationRun(
  runId: string
): Promise<VerificationRun> {
  const response = await apiClient.get<VerificationRun>(
    `/verification/runs/${runId}`
  );
  return response.data;
}

export async function getSpecificationEvidence(
  specificationId: string,
  projectId?: string
): Promise<RequirementEvidenceReport> {
  const url = projectId
    ? `/requirements/specifications/${specificationId}/evidence?project_id=${projectId}`
    : `/requirements/specifications/${specificationId}/evidence`;
  const response = await apiClient.get<RequirementEvidenceReport>(url);
  return response.data;
}

export async function getDockerStatus(): Promise<DockerStatusResponse> {
  const response = await apiClient.get<DockerStatusResponse>(
    "/verification/docker-status"
  );
  return response.data;
}
