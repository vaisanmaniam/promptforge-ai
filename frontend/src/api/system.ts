import { apiClient } from "./client";
import { HealthResponse, SystemStatusResponse } from "../types/system";

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>("/health");
  return response.data;
}

export async function fetchSystemStatus(): Promise<SystemStatusResponse> {
  const response = await apiClient.get<SystemStatusResponse>("/system/status");
  return response.data;
}
