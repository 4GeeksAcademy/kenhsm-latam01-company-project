export default function CandidateDetailLoading() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-10 md:px-10">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Detalle de candidatura</h1>
      </div>

      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium text-zinc-700">Cargando detalle de candidatura...</p>
      </section>
    </main>
  );
}