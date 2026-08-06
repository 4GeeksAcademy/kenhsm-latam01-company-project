"use client";

import { FormEvent, useState } from "react";
import { createCandidate } from "@/services/records";
import { CandidatePayload } from "@/types/records";

const STATUS_OPTIONS = ["received", "in_progress", "selected", "rejected"];
const STAGE_OPTIONS = ["pending", "review", "interview", "offer", "hired", "rejected"];

const INITIAL_FORM = {
  full_name: "",
  email: "",
  phone: "",
  position: "",
  linkedin_url: "",
  cv_url: "",
  status: "received",
  stage: "pending",
  experience_years: "0",
};

export default function CreateCandidateForm() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  function updateField(name: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function validateForm(): string | null {
    if (!form.full_name.trim()) return "Nombre completo es requerido.";
    if (!form.email.trim()) return "Email es requerido.";
    if (!form.phone.trim()) return "Telefono es requerido.";
    if (!form.position.trim()) return "Puesto es requerido.";
    if (!form.linkedin_url.trim()) return "LinkedIn es requerido.";
    if (!form.cv_url.trim()) return "Enlace de CV es requerido.";
    if (!form.status.trim()) return "Estado es requerido.";
    if (!form.stage.trim()) return "Etapa es requerida.";
    if (form.experience_years === "" || Number.isNaN(Number(form.experience_years))) {
      return "Anios de experiencia debe ser un numero.";
    }
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validationError = validateForm();
    if (validationError) {
      setFeedback({ type: "error", message: validationError });
      return;
    }

    const payload: CandidatePayload = {
      full_name: form.full_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim(),
      position: form.position.trim(),
      linkedin_url: form.linkedin_url.trim(),
      cv_url: form.cv_url.trim(),
      status: form.status,
      stage: form.stage,
      experience_years: Number(form.experience_years),
    };

    setIsSubmitting(true);
    setFeedback(null);

    try {
      await createCandidate(payload);

      setFeedback({ type: "success", message: "Candidatura creada correctamente." });
      setForm(INITIAL_FORM);
      window.dispatchEvent(new CustomEvent("candidate:created"));
    } catch {
      setFeedback({ type: "error", message: "No se pudo crear la candidatura." });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-zinc-900">Nueva candidatura</h2>

      <form onSubmit={handleSubmit} className="mt-4 grid gap-4 md:grid-cols-2">
        <Field label="Nombre completo" id="create-full-name">
          <input id="create-full-name" value={form.full_name} onChange={(e) => updateField("full_name", e.target.value)} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" />
        </Field>
        <Field label="Email" id="create-email">
          <input id="create-email" type="email" value={form.email} onChange={(e) => updateField("email", e.target.value)} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" />
        </Field>
        <Field label="Telefono" id="create-phone">
          <input id="create-phone" value={form.phone} onChange={(e) => updateField("phone", e.target.value)} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" />
        </Field>
        <Field label="Puesto" id="create-position">
          <input id="create-position" value={form.position} onChange={(e) => updateField("position", e.target.value)} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" />
        </Field>
        <Field label="LinkedIn" id="create-linkedin">
          <input id="create-linkedin" value={form.linkedin_url} onChange={(e) => updateField("linkedin_url", e.target.value)} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" />
        </Field>
        <Field label="Enlace CV" id="create-cv">
          <input id="create-cv" value={form.cv_url} onChange={(e) => updateField("cv_url", e.target.value)} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" />
        </Field>
        <Field label="Estado" id="create-status">
          <select id="create-status" value={form.status} onChange={(e) => updateField("status", e.target.value)} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm">
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </Field>
        <Field label="Etapa" id="create-stage">
          <select id="create-stage" value={form.stage} onChange={(e) => updateField("stage", e.target.value)} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm">
            {STAGE_OPTIONS.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </Field>
        <Field label="Anios de experiencia" id="create-exp">
          <input id="create-exp" type="number" min="0" value={form.experience_years} onChange={(e) => updateField("experience_years", e.target.value)} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" />
        </Field>

        <div className="md:col-span-2">
          <button type="submit" disabled={isSubmitting} className="inline-flex items-center rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60">
            {isSubmitting ? "Guardando..." : "Crear candidatura"}
          </button>
        </div>
      </form>

      {feedback ? (
        <p className={`mt-3 text-sm ${feedback.type === "success" ? "text-emerald-700" : "text-red-700"}`}>
          {feedback.message}
        </p>
      ) : null}
    </section>
  );
}

function Field({
  label,
  id,
  children,
}: {
  label: string;
  id: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-semibold uppercase tracking-wide text-zinc-600">
        {label}
      </label>
      {children}
    </div>
  );
}
