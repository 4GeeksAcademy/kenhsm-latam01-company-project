"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { patchCandidate } from "@/services/records";
import type { CandidateStage, CandidateStatus } from "@/types/records";
import { CANDIDATE_STAGES, CANDIDATE_STATUSES } from "@/lib/candidate-labels";

type CandidateUpdateControlsProps = {
  recordId: string;
  initialStatus: CandidateStatus;
  initialStage: CandidateStage;
};

export default function CandidateUpdateControls({
  recordId,
  initialStatus,
  initialStage,
}: CandidateUpdateControlsProps) {
  const router = useRouter();
  const [status, setStatus] = useState<CandidateStatus>(initialStatus);
  const [stage, setStage] = useState<CandidateStage>(initialStage);
  const [isSavingStatus, setIsSavingStatus] = useState(false);
  const [isSavingStage, setIsSavingStage] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  async function handleUpdateStatus(nextStatus: CandidateStatus) {
    setStatus(nextStatus);
    setIsSavingStatus(true);
    setFeedback(null);

    try {
      const updated = await patchCandidate(recordId, { status: nextStatus });
      setStatus(updated.status);
      setStage(updated.stage);
      setFeedback({ type: "success", message: "Estado actualizado correctamente." });
      router.refresh();
    } catch {
      setFeedback({ type: "error", message: "No se pudo actualizar el estado." });
    } finally {
      setIsSavingStatus(false);
    }
  }

  async function handleUpdateStage(nextStage: CandidateStage) {
    setStage(nextStage);
    setIsSavingStage(true);
    setFeedback(null);

    try {
      const updated = await patchCandidate(recordId, { stage: nextStage });
      setStatus(updated.status);
      setStage(updated.stage);
      setFeedback({ type: "success", message: "Etapa actualizada correctamente." });
      router.refresh();
    } catch {
      setFeedback({ type: "error", message: "No se pudo actualizar la etapa." });
    } finally {
      setIsSavingStage(false);
    }
  }

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h3 className="text-base font-semibold text-zinc-900">Actualizar estado y etapa</h3>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor="status-update" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-zinc-600">
            Estado
          </label>
          <select
            id="status-update"
            value={status}
            onChange={(event) => handleUpdateStatus(event.target.value as CandidateStatus)}
            disabled={isSavingStatus}
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {CANDIDATE_STATUSES.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="stage-update" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-zinc-600">
            Etapa
          </label>
          <select
            id="stage-update"
            value={stage}
            onChange={(event) => handleUpdateStage(event.target.value as CandidateStage)}
            disabled={isSavingStage}
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {CANDIDATE_STAGES.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {feedback ? (
        <p className={`mt-3 text-sm ${feedback.type === "success" ? "text-emerald-700" : "text-red-700"}`}>
          {feedback.message}
        </p>
      ) : null}
    </section>
  );
}
