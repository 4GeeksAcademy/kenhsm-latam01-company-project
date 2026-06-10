import { API_URL, parseJsonResponse } from "@/lib/api";
import { CandidateNote, NotesResponse } from "@/types/notes";

export async function fetchRecordNotes(recordId: string): Promise<NotesResponse> {
  const response = await fetch(`${API_URL}/records/${recordId}/notes`, {
    cache: "no-store",
  });

  return parseJsonResponse<NotesResponse>(response, "Failed to fetch notes");
}

export async function createRecordNote(recordId: string, content: string): Promise<CandidateNote> {
  const response = await fetch(`${API_URL}/records/${recordId}/notes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content }),
  });

  return parseJsonResponse<CandidateNote>(response, "Failed to create note");
}

export async function deleteRecordNote(recordId: string, noteId: string): Promise<void> {
  const response = await fetch(`${API_URL}/records/${recordId}/notes/${noteId}`, {
    method: "DELETE",
  });

  await parseJsonResponse<unknown>(response, "Failed to delete note");
}