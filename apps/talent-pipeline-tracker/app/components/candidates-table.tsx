"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

type CandidateRecord = {
  id: string;
  full_name: string;
  email: string;
  position: string;
  status: string;
  stage: string;
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

export default function CandidatesTable() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [candidates, setCandidates] = useState<CandidateRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isMounted = true;

    async function loadCandidates() {
      setIsLoading(true);
      setError(null);

      try {
        const pageSize = 50;
        const firstPage = await fetchRecordsPage(1, pageSize);
        const totalPages = Math.ceil(firstPage.total / pageSize);

        let allRecords = firstPage.data;

        if (totalPages > 1) {
          const remainingPages = await Promise.all(
            Array.from({ length: totalPages - 1 }, (_, index) => fetchRecordsPage(index + 2, pageSize)),
          );
          allRecords = [firstPage, ...remainingPages].flatMap((page) => page.data);
        }

        if (isMounted) {
          setCandidates(allRecords);
        }
      } catch {
        if (isMounted) {
          setError("No se pudieron cargar las candidaturas desde GET /records.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadCandidates();

    return () => {
      isMounted = false;
    };
  }, [reloadKey]);

  useEffect(() => {
    function handleCandidateCreated() {
      setReloadKey((current) => current + 1);
    }

    window.addEventListener("candidate:created", handleCandidateCreated);
    return () => {
      window.removeEventListener("candidate:created", handleCandidateCreated);
    };
  }, []);

  const selectedStatus = searchParams.get("status") ?? "all";
  const selectedStage = searchParams.get("stage") ?? "all";
  const searchQuery = searchParams.get("q") ?? "";

  const statuses = useMemo(
    () => Array.from(new Set(candidates.map((candidate) => candidate.status))).sort(),
    [candidates],
  );

  const stages = useMemo(
    () => Array.from(new Set(candidates.map((candidate) => candidate.stage))).sort(),
    [candidates],
  );

  const filteredCandidates = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();

    return candidates.filter((candidate) => {
      const statusMatches = selectedStatus === "all" || candidate.status === selectedStatus;
      const stageMatches = selectedStage === "all" || candidate.stage === selectedStage;
      const searchMatches =
        normalizedQuery.length === 0 ||
        candidate.full_name.toLowerCase().includes(normalizedQuery) ||
        candidate.email.toLowerCase().includes(normalizedQuery);

      return statusMatches && stageMatches && searchMatches;
    });
  }, [candidates, selectedStatus, selectedStage, searchQuery]);

  function updateParam(key: "status" | "stage" | "q", value: string) {
    const params = new URLSearchParams(searchParams.toString());

    if ((key === "q" && value.trim() === "") || (key !== "q" && value === "all")) {
      params.delete(key);
    } else {
      params.set(key, value);
    }

    const query = params.toString();
    router.push(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium text-zinc-700">Cargando candidaturas...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 shadow-sm">
        <p className="text-sm font-medium text-red-700">{error}</p>
        <button
          type="button"
          onClick={() => setReloadKey((current) => current + 1)}
          className="mt-3 inline-flex items-center rounded-md border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm md:grid-cols-4 md:items-end">
        <div>
          <label htmlFor="search-filter" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-zinc-600">
            Buscar por nombre o email
          </label>
          <input
            id="search-filter"
            type="search"
            value={searchQuery}
            onChange={(event) => updateParam("q", event.target.value)}
            placeholder="Ej: maria o maria@email.com"
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
          />
        </div>

        <div>
          <label htmlFor="status-filter" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-zinc-600">
            Filtro por estado
          </label>
          <select
            id="status-filter"
            value={selectedStatus}
            onChange={(event) => updateParam("status", event.target.value)}
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
          >
            <option value="all">Todos</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="stage-filter" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-zinc-600">
            Filtro por etapa
          </label>
          <select
            id="stage-filter"
            value={selectedStage}
            onChange={(event) => updateParam("stage", event.target.value)}
            className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
          >
            <option value="all">Todas</option>
            {stages.map((stage) => (
              <option key={stage} value={stage}>
                {stage}
              </option>
            ))}
          </select>
        </div>

        <p className="text-sm text-zinc-600 md:text-right">
          Mostrando <span className="font-semibold text-zinc-900">{filteredCandidates.length}</span> de {" "}
          <span className="font-semibold text-zinc-900">{candidates.length}</span>
        </p>
      </div>

      <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-zinc-200">
            <thead className="bg-zinc-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">
                  Nombre completo
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Puesto</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Estado actual</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Etapa actual</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">Detalle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 bg-white">
              {filteredCandidates.map((candidate) => (
                <tr key={candidate.id} className="hover:bg-zinc-50/80">
                  <td className="px-4 py-3 text-sm font-medium text-zinc-900">
                    {candidate.full_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-zinc-700">{candidate.position}</td>
                  <td className="px-4 py-3 text-sm text-zinc-700">{candidate.status}</td>
                  <td className="px-4 py-3 text-sm text-zinc-700">{candidate.stage}</td>
                  <td className="px-4 py-3 text-sm text-zinc-700">
                    <Link
                      href={`/candidates/${candidate.id}`}
                      className="inline-flex items-center rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-800 hover:bg-zinc-100"
                    >
                      Ver detalle
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredCandidates.length === 0 ? (
            <div className="border-t border-zinc-100 px-4 py-8 text-center text-sm text-zinc-600">
              No hay candidaturas para los filtros actuales.
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
