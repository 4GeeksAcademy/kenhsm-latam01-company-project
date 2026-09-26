"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearStoredToken } from "@/lib/auth";
import { useStoredToken } from "@/lib/use-stored-token";

export default function AccountNav() {
  const router = useRouter();
  const token = useStoredToken();
  const isAuthenticated = token !== null;

  function handleLogout() {
    clearStoredToken();
    router.push("/login");
  }

  if (!isAuthenticated) {
    return (
      <Link href="/login" className="text-xs font-semibold text-amber-800 hover:underline">
        Iniciar sesión
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Link href="/account/profile" className="text-xs font-semibold text-amber-800 hover:underline">
        Mi cuenta
      </Link>
      <button
        type="button"
        onClick={handleLogout}
        className="rounded-full border border-amber-300 bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 hover:bg-amber-200"
      >
        Cerrar sesión
      </button>
    </div>
  );
}
