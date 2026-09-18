import { clearStoredToken, getStoredToken } from "./auth";

// Thrown whenever a protected API call is rejected for missing/invalid/expired auth.
export class UnauthorizedError extends Error {
  constructor() {
    super("Sesión inválida o expirada.");
  }
}

// Attaches the stored JWT (if any) and clears it on 401 so AuthGuard reacts and redirects to /login.
export async function authenticatedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = getStoredToken();
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(input, { ...init, headers });

  if (response.status === 401) {
    clearStoredToken();
    throw new UnauthorizedError();
  }

  return response;
}
