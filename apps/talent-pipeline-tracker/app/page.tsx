type CandidateRecord = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  status: string;
  stage: string;
  experience_years: number;
  applied_at: string;
};

type RecordsResponse = {
  total: number;
  page: number;
  limit: number;
  data: CandidateRecord[];
};

const DEFAULT_API_URL = "https://playground.4geeks.com/tracker/api/v1";
const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(/\/$/, "");

async function fetchRecordsPage(page: number, limit: number): Promise<RecordsResponse> {
  const response = await fetch(`${API_URL}/records?page=${page}&limit=${limit}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch records: ${response.status}`);
  }

  return (await response.json()) as RecordsResponse;
}

async function fetchAllCandidates(): Promise<CandidateRecord[]> {
  const pageSize = 50;
  const firstPage = await fetchRecordsPage(1, pageSize);
  const totalPages = Math.ceil(firstPage.total / pageSize);

  if (totalPages <= 1) {
    return firstPage.data;
  }

  const remainingPages = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, index) => fetchRecordsPage(index + 2, pageSize)),
  );

  return [firstPage, ...remainingPages].flatMap((page) => page.data);
}

async function getCandidates(): Promise<
  { ok: true; data: CandidateRecord[] } | { ok: false; error: string }
> {
  try {
    const data = await fetchAllCandidates();
    return { ok: true, data };
  } catch {
    return { ok: false, error: "No se pudieron cargar las candidaturas" };
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-ES", { dateStyle: "medium" }).format(new Date(value));
}

export default async function Home() {
  const result = await getCandidates();

  if (!result.ok) {
    return (
      <main className="mx-auto flex w-full max-w-3xl flex-1 items-center justify-center px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          No se pudieron cargar las candidaturas desde el endpoint <strong>GET /records</strong>.
        </div>
      </main>
    );
  }

  const candidates = result.data;

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-10 md:px-10">
      <div className="mb-8 flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Listado de candidaturas</h1>
        <p className="text-sm text-zinc-600">
          Total de candidatos: <span className="font-semibold text-zinc-900">{candidates.length}</span>
        </p>
      </div>

      <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-zinc-200">
            <thead className="bg-zinc-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Nombre</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Email</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Posicion</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Estado</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Etapa</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Experiencia</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Aplico</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 bg-white">
              {candidates.map((candidate) => (
                <tr key={candidate.id} className="hover:bg-zinc-50/80">
                  <td className="px-4 py-3 text-sm font-medium text-zinc-900">{candidate.full_name}</td>
                  <td className="px-4 py-3 text-sm text-zinc-700">{candidate.email}</td>
                  <td className="px-4 py-3 text-sm text-zinc-700">{candidate.position}</td>
                  <td className="px-4 py-3 text-sm text-zinc-700">{candidate.status}</td>
                  <td className="px-4 py-3 text-sm text-zinc-700">{candidate.stage}</td>
                  <td className="px-4 py-3 text-sm text-zinc-700">{candidate.experience_years} anios</td>
                  <td className="px-4 py-3 text-sm text-zinc-700">{formatDate(candidate.applied_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
