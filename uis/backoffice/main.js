import { operationalSnapshot } from "./data.js";
import { Sidebar, DashboardHeader, KpiCard, ContextFact } from "./components.js";
import { mountApp } from "../shared/dom.js";

const app = document.querySelector("#app");
const apiBase = window.BRASALAND_API_URL || "";

mountApp("#app", () => `
    <div class="layout">
      ${Sidebar()}
      <main class="content">
        ${DashboardHeader(operationalSnapshot.dateLabel)}
        <section class="cards">
          ${operationalSnapshot.metrics.map((metric) => KpiCard(metric)).join("")}
        </section>
        ${ContextFact(operationalSnapshot.contextFact)}
        ${incidentManagementMarkup()}
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
  `);

  document.querySelector("#incident-form")?.addEventListener("submit", analyzeIncidents);
  document.querySelector("#new-incident-form")?.addEventListener("submit", createIncident);
  document.querySelector("#incident-filters")?.addEventListener("change", loadIncidents);
  document.querySelector("#new-incident-form select[name=origin]")?.addEventListener("change", (event) => document.querySelector("#branch-field")?.classList.toggle("is-highlighted", event.target.value === "branch"));
  loadIncidents();
}

const branchLabels = { central: "Central (Medellín / Miami)", medellin_centro: "Medellín Centro", medellin_laureles: "Medellín Laureles", medellin_envigado: "Medellín Envigado", medellin_bello: "Medellín Bello", medellin_itagui: "Medellín Itagüí", bogota_chapinero: "Bogotá Chapinero", bogota_usaquen: "Bogotá Usaquén", cali_granada: "Cali Granada", barranquilla_norte: "Barranquilla Norte", miami_doral: "Miami Doral", miami_hialeah: "Miami Hialeah", miami_kendall: "Miami Kendall", orlando_international: "Orlando International Drive", fort_lauderdale: "Fort Lauderdale" };
const categoryLabels = { equipment_failure: "Equipamiento", supply_issue: "Abastecimiento", customer_complaint: "Queja de cliente", staff_issue: "Personal", facility_issue: "Instalaciones", pos_system: "TPV", delivery_issue: "Delivery", other: "Otra" };

function incidentManagementMarkup() {
  const branchOptions = Object.entries(branchLabels).map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
  return `<section class="incident-panel" id="incident-management">
    <div class="section-heading"><div><p class="kicker">Operaciones en tiempo real</p><h2>Gestor de incidencias</h2></div><span id="incident-load-status" class="form-status" role="status"></span></div>
    <form id="new-incident-form" class="incident-form">
      <label>Título<input name="title" required maxlength="120" /></label>
      <label>Descripción<textarea name="description" required rows="3"></textarea></label>
      <label>Categoría<select name="category" required><option value="">Selecciona una categoría</option>${Object.entries(categoryLabels).map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}</select></label>
      <label>Estado<select name="status" required><option value="open">Abierta</option><option value="in_progress">En progreso</option><option value="resolved">Resuelta</option><option value="discarded">Descartada</option></select></label>
      <label>Origen<select name="origin" required><option value="">Selecciona un origen</option><option value="customer">Cliente</option><option value="branch">Sede</option><option value="internal">Central</option></select></label>
      <label id="branch-field">Sede<select name="branch" required><option value="">Selecciona una sede</option>${branchOptions}</select></label>
      <button type="submit">Registrar incidencia</button><p id="incident-form-status" class="form-status" role="status"></p>
    </form>
    <div id="incident-summary" class="incident-summary" aria-live="polite"></div>
    <div id="incident-filters" class="filters"><select name="status"><option value="">Todos los estados</option><option value="open">Abierta</option><option value="in_progress">En progreso</option><option value="resolved">Resuelta</option><option value="discarded">Descartada</option></select><select name="origin"><option value="">Todos los orígenes</option><option value="customer">Cliente</option><option value="branch">Sede</option><option value="internal">Central</option></select><select name="branch"><option value="">Todas las sedes</option>${branchOptions}</select></div>
    <div id="incident-list" class="incident-list" aria-live="polite"></div>
  </section>`;
}

async function createIncident(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button");
  const status = document.querySelector("#incident-form-status");
  button.disabled = true; status.textContent = "Registrando...";
  try {
    const payload = Object.fromEntries(new FormData(form));
    const response = await fetch(`${apiBase}/api/incidents`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error("No se pudo registrar la incidencia. Revisa los campos.");
    form.reset(); status.textContent = "Incidencia registrada correctamente."; await loadIncidents();
  } catch (error) { status.textContent = error.message; } finally { button.disabled = false; }
}

async function loadIncidents() {
  const list = document.querySelector("#incident-list");
  const filters = document.querySelector("#incident-filters");
  if (!list || !filters) return;
  list.innerHTML = "<p>Cargando incidencias...</p>";
  const params = new URLSearchParams([...filters.querySelectorAll("select")].filter((select) => select.value).map((select) => [select.name, select.value]));
  try {
    const [incidentsResponse, summaryResponse] = await Promise.all([fetch(`${apiBase}/api/incidents?${params}`), fetch(`${apiBase}/api/incidents/summary`)]);
    if (!incidentsResponse.ok || !summaryResponse.ok) throw new Error("No se pudieron cargar las incidencias.");
    const incidents = await incidentsResponse.json(); renderIncidentList(incidents); renderIncidentSummary(await summaryResponse.json());
  } catch (error) { list.innerHTML = `<p class="error-message">${error.message} <button type="button" id="retry-incidents">Reintentar</button></p>`; document.querySelector("#retry-incidents")?.addEventListener("click", loadIncidents); }
}

function renderIncidentList(incidents) {
  const list = document.querySelector("#incident-list");
  if (!incidents.length) { list.innerHTML = "<p>No hay incidencias que coincidan con los filtros.</p>"; return; }
  list.innerHTML = incidents.map((incident) => `<article class="incident-row"><div><strong>${escapeHtml(incident.title)}</strong><p>${escapeHtml(incident.description)}</p><small>${categoryLabels[incident.category] || incident.category} · ${branchLabels[incident.branch] || incident.branch}</small></div><label>Estado<select data-incident-id="${incident.id}" data-previous-status="${incident.status}">${statusOptions(incident.status)}</select></label></article>`).join("");
  list.querySelectorAll("select[data-incident-id]").forEach((select) => select.addEventListener("change", updateIncidentStatus));
}

function statusOptions(current) { return [["open", "Abierta"], ["in_progress", "En progreso"], ["resolved", "Resuelta"], ["discarded", "Descartada"]].map(([value, label]) => `<option value="${value}" ${value === current ? "selected" : ""}>${label}</option>`).join(""); }
async function updateIncidentStatus(event) {
  const select = event.currentTarget; const previous = select.dataset.previousStatus;
  try { const response = await fetch(`${apiBase}/api/incidents/${select.dataset.incidentId}/status`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: select.value }) }); if (!response.ok) throw new Error(); select.dataset.previousStatus = select.value; await loadIncidents(); }
  catch { select.value = previous; document.querySelector("#incident-load-status").textContent = "No se pudo actualizar el estado."; }
}
function renderIncidentSummary(summary) {
  const groups = [["Estado", summary.by_status], ["Categoría", summary.by_category], ["Origen", summary.by_origin], ["Sede", summary.by_branch]];
  document.querySelector("#incident-summary").innerHTML = `<span>Total <strong>${summary.total}</strong></span>${groups.flatMap(([label, values]) => Object.entries(values).map(([key, value]) => `<span>${label}: ${categoryLabels[key] || branchLabels[key] || key} <strong>${value}</strong></span>`)).join("")}`;
}
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character])); }

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
