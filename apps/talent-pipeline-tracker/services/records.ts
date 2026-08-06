import { API_URL, parseJsonResponse } from "@/lib/api";
import {
  CandidatePayload,
  CandidateRecordDetail,
  PatchResponse,
  RecordsResponse,
} from "@/types/records";

export async function fetchRecordsPage(page: number, limit: number): Promise<RecordsResponse> {
  const response = await fetch(`${API_URL}/records?page=${page}&limit=${limit}`, {
    cache: "no-store",
  });

  return parseJsonResponse<RecordsResponse>(response, "Failed to fetch records");
}

export async function fetchCandidateById(id: string): Promise<CandidateRecordDetail> {
  const response = await fetch(`${API_URL}/records/${id}`, {
    cache: "no-store",
  });

  return parseJsonResponse<CandidateRecordDetail>(response, "Failed to fetch candidate detail");
}

export async function createCandidate(payload: CandidatePayload): Promise<void> {
  const response = await fetch(`${API_URL}/records`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  await parseJsonResponse<unknown>(response, "Failed to create record");
}

export async function updateCandidate(recordId: string, payload: CandidatePayload): Promise<void> {
  const response = await fetch(`${API_URL}/records/${recordId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  await parseJsonResponse<unknown>(response, "Failed to update record");
}

export async function patchCandidate(
  recordId: string,
  payload: { status?: string; stage?: string },
): Promise<PatchResponse> {
  const response = await fetch(`${API_URL}/records/${recordId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse<PatchResponse>(response, "Patch failed");
}