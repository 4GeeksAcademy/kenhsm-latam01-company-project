import CandidatesTable from "./components/candidates-table";
import CreateCandidateForm from "./components/create-candidate-form";
export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 py-10 md:px-10">
      <div className="mb-8 flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Listado de candidaturas</h1>
        <p className="text-sm text-zinc-600">Busca, filtra y navega entre candidaturas sin recargar la pagina.</p>
      </div>

      <CreateCandidateForm />

      <CandidatesTable />
    </main>
  );
}
