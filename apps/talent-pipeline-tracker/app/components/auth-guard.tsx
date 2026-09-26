"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getStoredToken } from "@/lib/auth";
import { useStoredToken } from "@/lib/use-stored-token";

const PUBLIC_PATHS = ["/login", "/register"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const token = useStoredToken();
  const isPublicPath = PUBLIC_PATHS.includes(pathname);
  const isAuthenticated = token !== null;

  useEffect(() => {
    // Re-read localStorage directly: on a hard navigation, useSyncExternalStore's first
    // client render can still report the SSR snapshot (null) for one tick before it
    // resyncs, which would otherwise cause a false redirect for an authenticated user.
    if (!isPublicPath && getStoredToken() === null) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isAuthenticated, isPublicPath, pathname, router]);

  // Avoid flashing protected content while the redirect to /login resolves.
  if (!isPublicPath && !isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
