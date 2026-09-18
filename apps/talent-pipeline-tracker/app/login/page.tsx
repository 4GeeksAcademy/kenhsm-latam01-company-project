"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthApiError, login } from "@/services/auth";
import { setStoredToken } from "@/lib/auth";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError("Email y contraseña son requeridos.");
      return;
    }

    setIsSubmitting(true);
    try {
      const token = await login({ email: email.trim(), password });
      setStoredToken(token.access_token);
      const next = searchParams.get("next") ?? "/";
      router.replace(next);
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "Email o contraseña incorrectos.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto mt-16 w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h1 className="text-lg font-semibold text-zinc-900">Iniciar sesión</h1>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
        <Field label="Email" id="login-email">
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
          />
        </Field>
        <Field label="Contraseña" id="login-password">
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
          />
        </Field>

        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center justify-center rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Ingresando..." : "Ingresar"}
        </button>
      </form>

      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}

      <p className="mt-4 text-sm text-zinc-600">
        ¿No tienes cuenta?{" "}
        <Link href="/register" className="font-medium text-amber-700 hover:underline">
          Regístrate
        </Link>
      </p>
    </section>
  );
}

export default function LoginPage() {
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-8 md:px-10 md:py-10">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}

function Field({ label, id, children }: { label: string; id: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-zinc-600">
        {label}
      </label>
      {children}
    </div>
  );
}
