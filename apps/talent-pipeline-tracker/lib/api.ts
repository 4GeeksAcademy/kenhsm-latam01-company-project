const DEFAULT_API_URL = "https://playground.4geeks.com/tracker/api/v1";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(/\/$/, "");

export async function parseJsonResponse<T>(response: Response, errorPrefix: string): Promise<T> {
  if (!response.ok) {
    throw new Error(`${errorPrefix}: ${response.status}`);
  }

  return (await response.json()) as T;
}