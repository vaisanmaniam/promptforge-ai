import { apiClient } from "./client";
import {
  AnalyzePromptRequest,
  AnalyzePromptResponse,
  OptimizePromptRequest,
  OptimizePromptResponse,
} from "../types/prompt";

export async function analyzePrompt(
  data: AnalyzePromptRequest
): Promise<AnalyzePromptResponse> {
  const response = await apiClient.post<AnalyzePromptResponse>(
    "/prompts/analyze",
    data
  );
  return response.data;
}

export async function optimizePrompt(
  data: OptimizePromptRequest
): Promise<OptimizePromptResponse> {
  const response = await apiClient.post<OptimizePromptResponse>(
    "/prompts/optimize",
    data
  );
  return response.data;
}
