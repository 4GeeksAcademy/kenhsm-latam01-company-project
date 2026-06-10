"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { patchCandidate } from "@/services/records";

type CandidateUpdateControlsProps = {
  recordId: string;
  initialStatus: string;
  initialStage: string;
};

const DEFAULT_STATUS_OPTIONS = ["received", "in_progress", "selected", "rejected"];
const DEFAULT_STAGE_OPTIONS = ["pending", "review", "interview", "offer", "hired", "rejected"];

export default function CandidateUpdateControls({
  recordId,
  initialStatus,
  initialStage,
}: CandidateUpdateControlsProps) {
  const router = useRouter();
  const [status, setStatus] = useState(initialStatus);
  const [stage, setStage] = useState(initialStage);
  const [isSavingStatus, setIsSavingStatus] = useState(false);
  const [isSavingStage, setIsSavingStage] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const statusOptions = useMemo(() => {
    const options = new Set([...DEFAULT_STATUS_OPTIONS, initialStatus, status]);
    return Array.from(options);
  }, [initialStatus, status]);

  const stageOptions = useMemo(() => {
    const options = new Set([...DEFAULT_STAGE_OPTIONS, initialStage, stage]);
    return Array.from(options);
  }, [initialStage, stage]);

  async function handleUpdateStatus(nextStatus: string) {
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

  async function handleUpdateStage(nextStage: string) {
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
            onChange={(event) => handleUpdateStatus(event.target.value)}
            disabled={isSavingStatus}
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                {option}
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
            onChange={(event) => handleUpdateStage(event.target.value)}
            disabled={isSavingStage}
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {stageOptions.map((option) => (
              <option key={option} value={option}>
                {option}
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
