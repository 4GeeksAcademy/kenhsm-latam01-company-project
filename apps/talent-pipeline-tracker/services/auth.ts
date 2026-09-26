import { AUTH_API_URL } from "@/lib/auth";
import { authenticatedFetch } from "@/lib/auth-fetch";
import {
  CurrentUser,
  LoginPayload,
  ProfileOut,
  ProfileUpdatePayload,
  RegisterPayload,
  TokenResponse,
} from "@/types/auth";

// Carries the backend's field-level detail so callers can show precise validation errors.
export class AuthApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseAuthResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    let detail = fallbackMessage;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") {
        detail = data.detail;
      } else if (Array.isArray(data?.detail)) {
        detail = data.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(" ") || fallbackMessage;
      }
    } catch {
      // Response had no JSON body; keep the fallback message.
    }
    throw new AuthApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const body = new URLSearchParams();
  body.set("username", payload.email);
  body.set("password", payload.password);

  const response = await fetch(`${AUTH_API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  return parseAuthResponse<TokenResponse>(response, "Email o contraseña incorrectos.");
}

export async function registerUser(payload: RegisterPayload): Promise<void> {
  const response = await fetch(`${AUTH_API_URL}/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  await parseAuthResponse<unknown>(response, "No se pudo registrar el usuario.");
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const response = await authenticatedFetch(`${AUTH_API_URL}/auth/me`, { cache: "no-store" });
  return parseAuthResponse<CurrentUser>(response, "No se pudo obtener el usuario actual.");
}

export async function updateMyProfile(payload: ProfileUpdatePayload): Promise<ProfileOut> {
  const response = await authenticatedFetch(`${AUTH_API_URL}/profiles/me`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return parseAuthResponse<ProfileOut>(response, "No se pudo actualizar el perfil.");
}
