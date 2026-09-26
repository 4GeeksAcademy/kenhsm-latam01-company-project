"use client";

import { FormEvent, useEffect, useState } from "react";
import { fetchCurrentUser, updateMyProfile } from "@/services/auth";
import { UnauthorizedError } from "@/lib/auth-fetch";
import { CurrentUser } from "@/types/auth";

export default function AccountProfilePage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [form, setForm] = useState({ name: "", phone: "", address: "" });
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    fetchCurrentUser()
      .then((user) => {
        setCurrentUser(user);
        setForm({
          name: user.profile?.name ?? "",
          phone: user.profile?.phone ?? "",
          address: user.profile?.address ?? "",
        });
        setIsLoading(false);
      })
      .catch((err) => {
        // On UnauthorizedError the token was already cleared; AuthGuard will redirect to /login shortly.
        if (!(err instanceof UnauthorizedError)) {
          setIsLoading(false);
        }
      });
  }, []);

  function updateField(name: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setIsSubmitting(true);
    setFeedback(null);
    try {
      const profile = await updateMyProfile(form);
      setCurrentUser((current) => (current ? { ...current, profile } : current));
      setFeedback({ type: "success", message: "Perfil actualizado correctamente." });
    } catch {
      setFeedback({ type: "error", message: "No se pudo actualizar el perfil." });
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-8 md:px-10 md:py-10">
        <p className="text-sm text-zinc-600">Cargando cuenta...</p>
      </main>
    );
  }

  if (!currentUser) {
    return null;
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-8 md:px-10 md:py-10">
      <div className="mb-8 rounded-2xl border border-amber-200/80 bg-[var(--surface)] p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">Mi cuenta</p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-zinc-900">{currentUser.email}</h1>
        <p className="mt-1 text-sm text-zinc-700">Rol: {currentUser.role}</p>
      </div>

      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-zinc-900">Datos de perfil</h2>

        <form onSubmit={handleSubmit} className="mt-4 grid gap-4 md:grid-cols-2">
          <Field label="Nombre" id="account-name">
            <input
              id="account-name"
              value={form.name}
              onChange={(e) => updateField("name", e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Teléfono" id="account-phone">
            <input
              id="account-phone"
              value={form.phone}
              onChange={(e) => updateField("phone", e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Dirección" id="account-address">
            <input
              id="account-address"
              value={form.address}
              onChange={(e) => updateField("address", e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
            />
          </Field>

          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
        </form>

        {feedback ? (
          <p className={`mt-3 text-sm ${feedback.type === "success" ? "text-emerald-700" : "text-red-700"}`}>
            {feedback.message}
          </p>
        ) : null}
      </section>
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
