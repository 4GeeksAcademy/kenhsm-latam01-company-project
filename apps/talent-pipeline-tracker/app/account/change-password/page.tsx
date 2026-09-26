"use client";

import { FormEvent, useState } from "react";
import { AuthApiError, changePassword } from "@/services/auth";

export default function ChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    if (password !== confirmation) {
      setFeedback({ type: "error", message: "Las contraseñas nuevas no coinciden." });
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await changePassword({ current_password: currentPassword, new_password: password });
      setFeedback({ type: "success", message: response.message });
      setCurrentPassword("");
      setPassword("");
      setConfirmation("");
    } catch (err) {
      setFeedback({
        type: "error",
        message: err instanceof AuthApiError ? err.message : "No se pudo actualizar la contraseña.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-8 md:px-10 md:py-10">
      <section className="w-full max-w-xl rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold text-zinc-900">Cambiar contraseña</h1>
        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          <PasswordField id="current-password" label="Contraseña actual" value={currentPassword} onChange={setCurrentPassword} />
          <PasswordField id="new-password" label="Nueva contraseña" value={password} onChange={setPassword} />
          <PasswordField id="new-password-confirmation" label="Confirmar nueva contraseña" value={confirmation} onChange={setConfirmation} />
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center justify-center rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Actualizando..." : "Actualizar contraseña"}
          </button>
        </form>
        {feedback ? (
          <p className={`mt-3 text-sm ${feedback.type === "success" ? "text-emerald-700" : "text-red-700"}`} role="status">
            {feedback.message}
          </p>
        ) : null}
      </section>
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
        autoComplete="current-password"
        minLength={8}
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
      />
    </div>
  );
}