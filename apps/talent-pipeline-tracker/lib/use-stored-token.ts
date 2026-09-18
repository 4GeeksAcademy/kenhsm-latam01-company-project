import { useSyncExternalStore } from "react";
import { getStoredToken, subscribeToStoredToken } from "./auth";

function getServerSnapshot(): string | null {
  return null;
}

// Reads the JWT from localStorage reactively (updates on login/logout, including other tabs).
export function useStoredToken(): string | null {
  return useSyncExternalStore(subscribeToStoredToken, getStoredToken, getServerSnapshot);
}
