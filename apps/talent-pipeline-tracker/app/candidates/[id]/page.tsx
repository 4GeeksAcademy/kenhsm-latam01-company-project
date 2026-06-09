import Link from "next/link";
import { notFound } from "next/navigation";
import CandidateEditForm from "./candidate-edit-form";
import CandidateUpdateControls from "./candidate-update-controls";
import CandidateNotesSection from "./candidate-notes-section";

type CandidateRecordDetail = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  cv_url: string;
  status: string;
  stage: string;
  experience_years: number;
  notes_count: number;
  applied_at: string;
  updated_at: string;
};

const DEFAULT_API_URL = "https://playground.4geeks.com/tracker/api/v1";
const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(/\/$/, "");

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

async function fetchCandidateById(id: string): Promise<CandidateRecordDetail> {
  const response = await fetch(`${API_URL}/records/${id}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch candidate detail: ${response.status}`);
  }

  return (await response.json()) as CandidateRecordDetail;
}

async function getCandidate(
  id: string,
): Promise<
  | { ok: true; data: CandidateRecordDetail }
  | { ok: false; notFound: true }
  | { ok: false; notFound: false }
> {
  try {
    const data = await fetchCandidateById(id);
    return { ok: true, data };
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) {
      return { ok: false, notFound: true };
    }

    return { ok: false, notFound: false };
  }
}

export default async function CandidateDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const result = await getCandidate(id);

  if (!result.ok && result.notFound) {
    notFound();
  }

  if (!result.ok) {
    return (
      <main className="mx-auto flex w-full max-w-3xl flex-1 items-center justify-center px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          No se pudo cargar el detalle de la candidatura desde <strong>GET /records/:id</strong>.
        </div>
      </main>
    );
  }

  const candidate = result.data;

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-10 md:px-10">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Detalle de candidatura</h1>
        <Link
          href="/"
          className="inline-flex items-center rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-100"
        >
          Volver al listado
        </Link>
      </div>

      <CandidateUpdateControls
        recordId={candidate.id}
        initialStatus={candidate.status}
        initialStage={candidate.stage}
      />

      <CandidateEditForm
        recordId={candidate.id}
        initialValues={{
          full_name: candidate.full_name,
          email: candidate.email,
          phone: candidate.phone,
          position: candidate.position,
          linkedin_url: candidate.linkedin_url,
          cv_url: candidate.cv_url,
          status: candidate.status,
          stage: candidate.stage,
          experience_years: candidate.experience_years,
        }}
      />

      <CandidateNotesSection recordId={candidate.id} />

      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-zinc-900">{candidate.full_name}</h2>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <DetailItem label="Nombre completo" value={candidate.full_name} />
          <DetailItem label="Email" value={candidate.email} />
          <DetailItem label="Telefono" value={candidate.phone} />
          <DetailItem label="Puesto" value={candidate.position} />
          <DetailItem label="LinkedIn" value={candidate.linkedin_url} isLink />
          <DetailItem label="Enlace al CV" value={candidate.cv_url} isLink />
          <DetailItem label="Anios de experiencia" value={`${candidate.experience_years} anios`} />
          <DetailItem label="Estado" value={candidate.status} />
          <DetailItem label="Etapa" value={candidate.stage} />
          <DetailItem label="Fecha de postulacion" value={formatDate(candidate.applied_at)} />
        </div>
      </section>
    </main>
  );
}

function DetailItem({
  label,
  value,
  isLink = false,
}: {
  label: string;
  value: string;
  isLink?: boolean;
}) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{label}</p>
      {isLink ? (
        <a
          href={value}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 block break-all text-sm font-medium text-zinc-900 hover:underline"
        >
          {value}
        </a>
      ) : (
        <p className="mt-1 break-all text-sm font-medium text-zinc-900">{value}</p>
      )}
    </div>
  );
}
