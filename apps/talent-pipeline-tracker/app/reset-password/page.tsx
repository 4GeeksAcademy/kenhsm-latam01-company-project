"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthApiError, resetPassword } from "@/services/auth";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!token) {
      setError("El enlace no contiene un token. Solicita uno nuevo.");
      return;
    }
    if (password !== confirmation) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setIsSubmitting(true);
    try {
      await resetPassword({ token, new_password: password });
      router.replace("/login?passwordReset=1");
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "El enlace es inválido o ha expirado.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto mt-8 w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h1 className="text-lg font-semibold text-zinc-900">Crear nueva contraseña</h1>
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
        <PasswordField id="reset-password" label="Nueva contraseña" value={password} onChange={setPassword} />
        <PasswordField id="reset-confirmation" label="Confirmar contraseña" value={confirmation} onChange={setConfirmation} />
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center justify-center rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Actualizando..." : "Actualizar contraseña"}
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-red-700" role="alert">{error}</p> : null}
      <p className="mt-4 text-sm">
        <Link href="/forgot-password" className="font-medium text-amber-700 hover:underline">
          Solicitar otro enlace
        </Link>
      </p>
    </section>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-8 md:px-10 md:py-10">
      <Suspense fallback={<p className="mx-auto mt-8 text-sm text-zinc-600">Cargando formulario...</p>}>
        <ResetPasswordForm />
      </Suspense>
    </main>
  );
}

function PasswordField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-zinc-600">
        {label}
      </label>
      <input
        id={id}
        type="password"
        autoComplete="new-password"
        minLength={8}
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
      />
    </div>
  );
}