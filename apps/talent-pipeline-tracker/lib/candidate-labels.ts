import type { CandidateStage, CandidateStatus } from "@/types/records";

export const CANDIDATE_STATUSES: ReadonlyArray<{ value: CandidateStatus; label: string }> = [
  { value: "received", label: "Recibida" },
  { value: "in_progress", label: "En proceso" },
  { value: "selected", label: "Seleccionada" },
  { value: "discarded", label: "Descartada" },
];

export const CANDIDATE_STAGES: ReadonlyArray<{ value: CandidateStage; label: string }> = [
  { value: "pending", label: "Pendiente de revisión" },
  { value: "review", label: "En revisión" },
  { value: "personal_interview", label: "Entrevista personal" },
  { value: "technical_interview", label: "Entrevista técnica" },
  { value: "offer_presented", label: "Oferta presentada" },
];

export const CANDIDATE_STATUS_LABELS: Record<CandidateStatus, string> = {
  received: "Recibida",
  in_progress: "En proceso",
  selected: "Seleccionada",
  discarded: "Descartada",
};

export const CANDIDATE_STAGE_LABELS: Record<CandidateStage, string> = {
  pending: "Pendiente de revisión",
  review: "En revisión",
  personal_interview: "Entrevista personal",
  technical_interview: "Entrevista técnica",
  offer_presented: "Oferta presentada",
};