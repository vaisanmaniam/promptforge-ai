import { apiClient } from './client';
import {
  FailureAnalysisReport,
  GenerateProposalRequest,
  PatchApplicationResult,
  RepairAuditLogEntry,
  RepairProposal,
  RepairRuntimeStatus,
  RepairVerificationComparison,
} from '../types/repair';

export async function analyzeRunFailures(
  runId: string
): Promise<FailureAnalysisReport[]> {
  const response = await apiClient.post<FailureAnalysisReport[]>(
    `/repair/analyze/${runId}`
  );
  return response.data;
}

export async function getFailureReport(
  failureId: string
): Promise<FailureAnalysisReport> {
  const response = await apiClient.get<FailureAnalysisReport>(
    `/repair/failures/${failureId}`
  );
  return response.data;
}

export async function generateProposal(
  request: GenerateProposalRequest
): Promise<RepairProposal> {
  const response = await apiClient.post<RepairProposal>(
    '/repair/proposals',
    request
  );
  return response.data;
}

export async function listProposals(
  projectId?: string
): Promise<RepairProposal[]> {
  const params: Record<string, string> = {};
  if (projectId) {
    params.project_id = projectId;
  }
  const response = await apiClient.get<RepairProposal[]>('/repair/proposals', {
    params,
  });
  return response.data;
}

export async function getProposal(
  repairId: string
): Promise<RepairProposal> {
  const response = await apiClient.get<RepairProposal>(
    `/repair/proposals/${repairId}`
  );
  return response.data;
}

export async function approveProposal(
  repairId: string,
  reason?: string
): Promise<RepairProposal> {
  const response = await apiClient.post<RepairProposal>(
    `/repair/proposals/${repairId}/approve`,
    reason ? { decision_reason: reason } : {}
  );
  return response.data;
}

export async function rejectProposal(
  repairId: string,
  reason?: string
): Promise<RepairProposal> {
  const response = await apiClient.post<RepairProposal>(
    `/repair/proposals/${repairId}/reject`,
    reason ? { decision_reason: reason } : {}
  );
  return response.data;
}

export async function applyProposal(
  repairId: string
): Promise<PatchApplicationResult> {
  const response = await apiClient.post<PatchApplicationResult>(
    `/repair/proposals/${repairId}/apply`
  );
  return response.data;
}

export async function verifyProposal(
  repairId: string
): Promise<RepairVerificationComparison> {
  const response = await apiClient.post<RepairVerificationComparison>(
    `/repair/proposals/${repairId}/verify`
  );
  return response.data;
}

export async function rollbackProposal(
  repairId: string
): Promise<{ success: boolean; repair_id: string; status: string; message: string }> {
  const response = await apiClient.post<{
    success: boolean;
    repair_id: string;
    status: string;
    message: string;
  }>(`/repair/proposals/${repairId}/rollback`);
  return response.data;
}

export async function getRepairHistory(
  repairId?: string
): Promise<RepairAuditLogEntry[]> {
  const params: Record<string, string> = {};
  if (repairId) {
    params.repair_id = repairId;
  }
  const response = await apiClient.get<RepairAuditLogEntry[]>(
    '/repair/history',
    { params }
  );
  return response.data;
}

export async function getRepairRuntimeStatus(): Promise<RepairRuntimeStatus> {
  const response = await apiClient.get<RepairRuntimeStatus>(
    '/repair/runtime/status'
  );
  return response.data;
}
