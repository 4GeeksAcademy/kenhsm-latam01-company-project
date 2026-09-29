"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { AuthApiError, requestPasswordReset } from "@/services/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await requestPasswordReset(email.trim());
      setIsSubmitted(true);
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "No se pudo enviar la solicitud. Inténtalo nuevamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-8 md:px-10 md:py-10">
      <section className="mx-auto mt-8 w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold text-zinc-900">Recuperar contraseña</h1>
        {isSubmitted ? (
          <p className="mt-4 text-sm text-emerald-700" role="status">
            Si esa dirección está registrada, recibirás un enlace en breve.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
            <div>
              <label htmlFor="forgot-email" className="mb-1 block text-xs font-medium text-zinc-600">
                Email
              </label>
              <input
                id="forgot-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={isSubmitting}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={isSubmitting || isSubmitted}
              className="inline-flex items-center justify-center rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "Enviando..." : "Enviar enlace"}
            </button>
          </form>
        )}
        {error ? <p className="mt-3 text-sm text-red-700" role="alert">{error}</p> : null}
        <p className="mt-4 text-sm">
          <Link href="/login" className="font-medium text-amber-700 hover:underline">
            Volver a iniciar sesión
          </Link>
        </p>
      </section>
    </main>
  );
}