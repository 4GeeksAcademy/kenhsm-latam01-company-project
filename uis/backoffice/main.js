import { operationalSnapshot } from "./data.js";
import { Sidebar, DashboardHeader, KpiCard, ContextFact } from "./components.js";

const app = document.querySelector("#app");
const apiBase = window.BRASALAND_API_URL || "http://127.0.0.1:8000";

if (app) {
  app.innerHTML = `
    <div class="layout">
      ${Sidebar()}
      <main class="content">
        ${DashboardHeader(operationalSnapshot.dateLabel)}
        <section class="cards">
          ${operationalSnapshot.metrics.map((metric) => KpiCard(metric)).join("")}
        </section>
        ${ContextFact(operationalSnapshot.contextFact)}
        <section class="analysis-panel" id="incident-analysis">
          <div class="section-heading">
            <div>
              <p class="kicker">Control de calidad de datos</p>
              <h2>Análisis de incidencias</h2>
            </div>
            <a class="download-button is-disabled" id="download-results" href="#" download="results.csv" aria-disabled="true">Descargar CSV</a>
          </div>
          <form id="incident-form" class="upload-form">
            <label for="incident-file">Selecciona el CSV mensual de incidencias</label>
            <input id="incident-file" name="file" type="file" accept=".csv,text/csv" required />
            <button type="submit">Analizar fichero</button>
          </form>
          <p class="form-status" id="form-status" role="status"></p>
          <div id="analysis-result" class="analysis-result" aria-live="polite"></div>
        </section>
      </main>
    </div>
  `;

  document.querySelector("#incident-form")?.addEventListener("submit", analyzeIncidents);
}

async function analyzeIncidents(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const fileInput = form.querySelector("input[type=file]");
  const status = document.querySelector("#form-status");
  const result = document.querySelector("#analysis-result");
  const download = document.querySelector("#download-results");
  const file = fileInput.files[0];
  if (!file) return;

  status.textContent = "Analizando...";
  result.innerHTML = "";
  download.classList.add("is-disabled");
  download.setAttribute("aria-disabled", "true");
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${apiBase}/api/incidents/analyze`, { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "No se pudo analizar el fichero.");
    status.textContent = "Análisis completado.";
    result.innerHTML = renderAnalysis(payload);
    download.href = `${apiBase}/api/incidents/results/export`;
    download.classList.remove("is-disabled");
    download.removeAttribute("aria-disabled");
  } catch (error) {
    status.textContent = error.message;
    result.innerHTML = "";
  }
}

function renderAnalysis(data) {
  const categoryRows = renderRows(data.by_category, data.valid_records);
  const statusRows = renderRows(data.by_status, data.valid_records);
  const scoreRows = renderRows(data.satisfaction.counts, data.satisfaction.scored_cases, "Puntuación");
  const invalidLabels = {
    missing_location_id: "Falta location_id",
    invalid_or_missing_category: "Categoría inválida o faltante",
    empty_description: "Descripción vacía o demasiado corta",
    missing_reporter_id: "Falta reporter_id",
    closed_without_score: "Caso cerrado sin puntuación",
    score_out_of_range: "Puntuación fuera de rango",
    invalid_or_missing_status: "Estado inválido o faltante",
  };
  const invalidRows = Object.entries(data.invalid_breakdown)
    .filter(([, value]) => value > 0)
    .map(([key, value]) => `<li><span>${invalidLabels[key] || key}</span><strong>${value}</strong></li>`)
    .join("");
  const satisfaction = data.satisfaction;
  const average = satisfaction.average == null ? "N/A" : satisfaction.average.toFixed(2);
  return `
    <div class="summary-grid">
      <article><span>Total</span><strong>${data.total_records}</strong></article>
      <article><span>Válidos</span><strong>${data.valid_records}</strong></article>
      <article><span>Inválidos</span><strong>${data.invalid_records}</strong></article>
      <article><span>Promedio cerrado</span><strong>${average} / 5</strong></article>
    </div>
    <div class="analysis-columns">
      <div><h3>Incidencias inválidas</h3><ul>${invalidRows || "<li><span>Ninguna</span><strong>0</strong></li>"}</ul></div>
      <div><h3>Por categoría</h3><ul>${categoryRows}</ul></div>
      <div><h3>Por estado</h3><ul>${statusRows}</ul></div>
      <div><h3>Satisfacción</h3><ul>${scoreRows}</ul></div>
    </div>
    <p class="satisfaction-note">Casos cerrados con puntuación: ${satisfaction.scored_cases} de ${satisfaction.closed_cases}</p>
  `;
}

function renderRows(values, total, label = "") {
  return Object.entries(values).map(([key, value]) => {
    const percentage = total ? (value / total * 100).toFixed(1) : "0.0";
    const title = label ? `${label} ${key}` : key;
    return `<li><span>${title}</span><strong>${value} <small>(${percentage}%)</small></strong></li>`;
  }).join("");
}
