import CandidatesTable from "./components/candidates-table";
import CreateCandidateForm from "./components/create-candidate-form";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-8 md:px-10 md:py-10">
      <div className="fade-up mb-8 rounded-2xl border border-amber-200/80 bg-[var(--surface)] p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">People & Talent</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-zinc-900">Pipeline de candidaturas</h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-700">
          Gestiona postulaciones para Brasaland en un solo lugar: crea candidaturas, filtra por estado y etapa,
          y entra al detalle sin perder el contexto del listado.
        </p>
      </div>

      <CreateCandidateForm />

      <CandidatesTable />
    </main>
  );
}
