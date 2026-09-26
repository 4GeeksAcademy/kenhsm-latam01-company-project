const DEFAULT_AUTH_API_URL = "http://127.0.0.1:8010";

export const AUTH_API_URL = (process.env.NEXT_PUBLIC_AUTH_API_URL ?? DEFAULT_AUTH_API_URL).replace(/\/$/, "");

const TOKEN_STORAGE_KEY = "brasaland_access_token";
const TOKEN_EVENT = "brasaland-token-changed";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  window.dispatchEvent(new Event(TOKEN_EVENT));
}

export function clearStoredToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  window.dispatchEvent(new Event(TOKEN_EVENT));
}

// Notifies subscribers both on cross-tab changes ("storage") and same-tab changes (custom event).
export function subscribeToStoredToken(callback: () => void): () => void {
  window.addEventListener("storage", callback);
  window.addEventListener(TOKEN_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(TOKEN_EVENT, callback);
  };
}
