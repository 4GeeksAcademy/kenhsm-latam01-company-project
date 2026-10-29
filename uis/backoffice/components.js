export function Sidebar() {
  return `
    <aside class="sidebar">
      <h1>Backoffice</h1>
      <nav>
        <a href="#operations">Operaciones</a>
        <a href="./reporting.html">Reporte semanal</a>
        <a href="./telemetry.html">Reporte técnico</a>
        <a href="./rfp-intake.html">Recepción RFP</a>
        <a href="./manager-chat.html">Asistente en vivo</a>
        <a href="#incident-management">Gestor de incidencias</a>
        <a href="#incident-analysis">Análisis CSV</a>
        <a href="./suppliers.html">Directorio de Proveedores</a>
        <a href="#procurement">Compras</a>
        <a href="#people">Personas</a>
        <a href="#training">Formación</a>
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
