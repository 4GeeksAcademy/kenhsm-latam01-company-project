export function Sidebar() {
  return `
    <aside class="sidebar">
      <h1>Backoffice</h1>
      <nav>
        <a href="#">Operaciones</a>
        <a href="#incident-analysis">Análisis de incidencias</a>
        <a href="#">Compras</a>
        <a href="#">Personas</a>
        <a href="#">Formacion</a>
      </nav>
    </aside>
  `;
}

export function DashboardHeader(title) {
  return `
    <header>
      <p class="kicker">Vista de entrada</p>
      <h2>${title}</h2>
    </header>
  `;
}

export function KpiCard(metric) {
  return `
    <article>
      <h3>${metric.label}</h3>
      <p>${metric.value}</p>
    </article>
  `;
}

export function ContextFact(fact) {
  return `<p class="fact">${fact}</p>`;
}
