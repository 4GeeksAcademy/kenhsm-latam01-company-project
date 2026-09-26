"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthApiError, login, registerUser } from "@/services/auth";
import { setStoredToken } from "@/lib/auth";

const INITIAL_FORM = {
  email: "",
  password: "",
  name: "",
  phone: "",
  address: "",
};

type FieldErrors = Partial<Record<keyof typeof INITIAL_FORM, string>>;

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState(INITIAL_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);

  function updateField(name: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function validateForm(): FieldErrors {
    const errors: FieldErrors = {};
    if (!form.email.trim()) {
      errors.email = "Email es requerido.";
    }
    if (form.password.length < 8) {
      errors.password = "La contraseña debe tener al menos 8 caracteres.";
    }
    return errors;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const validationErrors = validateForm();
    setFieldErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      await registerUser({
        email: form.email.trim(),
        password: form.password,
        name: form.name.trim() || undefined,
        phone: form.phone.trim() || undefined,
        address: form.address.trim() || undefined,
      });

      const token = await login({ email: form.email.trim(), password: form.password });
      setStoredToken(token.access_token);
      router.replace("/");
    } catch (err) {
      if (err instanceof AuthApiError && err.status === 400) {
        // e.g. "Ya existe un usuario con ese email." from POST /users
        setFieldErrors({ email: err.message });
      } else {
        setFormError("No se pudo completar el registro. Intenta nuevamente.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-8 md:px-10 md:py-10">
      <section className="mx-auto mt-8 w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold text-zinc-900">Crear cuenta</h1>

        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          <Field label="Email" id="register-email" error={fieldErrors.email}>
            <input
              id="register-email"
              type="email"
              value={form.email}
              onChange={(e) => updateField("email", e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Contraseña" id="register-password" error={fieldErrors.password}>
            <input
              id="register-password"
              type="password"
              value={form.password}
              onChange={(e) => updateField("password", e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Nombre" id="register-name">
            <input
              id="register-name"
              value={form.name}
              onChange={(e) => updateField("name", e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Teléfono" id="register-phone">
            <input
              id="register-phone"
              value={form.phone}
              onChange={(e) => updateField("phone", e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
            />
          </Field>
          <Field label="Dirección" id="register-address">
            <input
              id="register-address"
              value={form.address}
              onChange={(e) => updateField("address", e.target.value)}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
            />
          </Field>

          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center justify-center rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Creando cuenta..." : "Registrarme"}
          </button>
        </form>

        {formError ? <p className="mt-3 text-sm text-red-700">{formError}</p> : null}

        <p className="mt-4 text-sm text-zinc-600">
          ¿Ya tienes cuenta?{" "}
          <Link href="/login" className="font-medium text-amber-700 hover:underline">
            Inicia sesión
          </Link>
        </p>
      </section>
    </main>
  );
}

function Field({
  label,
  id,
  error,
  children,
}: {
  label: string;
  id: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-zinc-600">
        {label}
      </label>
      {children}
      {error ? <p className="mt-1 text-xs text-red-700">{error}</p> : null}
    </div>
  );
}

