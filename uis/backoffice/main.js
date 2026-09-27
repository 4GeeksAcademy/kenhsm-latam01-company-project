import { operationalSnapshot } from "./data.js";
import { Sidebar, DashboardHeader, KpiCard, ContextFact } from "./components.js";
import { loadPublicConfig } from "./runtime-config.mjs";
import { track } from "./src/services/telemetry.mjs";

const app = document.querySelector("#app");
const runtimeConfig = await loadPublicConfig();
const apiBase = runtimeConfig.NEXT_PUBLIC_ADMIN_API_ENDPOINT || window.BRASALAND_API_URL || "http://127.0.0.1:8001";
let activeWorkflow = null;
let abandonmentTimer = null;

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
  document.querySelector("#incident-file")?.addEventListener("change", startIncidentWorkflow);
  app.addEventListener("click", trackNavigation);
  track("section_viewed", { section_id: "operations", client_area: "backoffice", navigation_source: "unknown" });
}

window.addEventListener("error", (event) => {
  trackFrontendError(event.error?.name || "Error", "error");
});

window.addEventListener("unhandledrejection", (event) => {
  trackFrontendError(event.reason?.name || typeof event.reason, "error");
});

window.addEventListener("pagehide", () => {
  abandonIncidentWorkflow("route_exit");
});

function trackNavigation(event) {
  const link = event.target.closest("nav a");
  if (!link) return;
  const sectionId = link.getAttribute("href") === "#incident-analysis"
    ? "incident_analysis"
    : link.textContent.trim() === "Operaciones" ? "operations" : null;
  if (!sectionId) return;
  track("section_viewed", { section_id: sectionId, client_area: "backoffice", navigation_source: "menu" });
}

function startIncidentWorkflow(event) {
  const file = event.currentTarget.files[0];
  if (!file || activeWorkflow) return;
  activeWorkflow = { id: createUuid(), startedAt: Date.now(), fileSizeBytes: file.size, step: "file_selected" };
  track("workflow_started", {
    workflow_id: "incident_analysis",
    workflow_instance_id: activeWorkflow.id,
    entry_source: "menu",
  });
  clearTimeout(abandonmentTimer);
  abandonmentTimer = setTimeout(() => abandonIncidentWorkflow("inactive_timeout"), 30 * 60 * 1000);
}

function completeIncidentWorkflow() {
  if (!activeWorkflow) return;
  track("workflow_completed", {
    workflow_id: "incident_analysis",
    workflow_instance_id: activeWorkflow.id,
    elapsed_seconds: Math.floor((Date.now() - activeWorkflow.startedAt) / 1000),
  });
  activeWorkflow = null;
  clearTimeout(abandonmentTimer);
}

function abandonIncidentWorkflow(completionState) {
  if (!activeWorkflow) return;
  track("workflow_abandoned", {
    workflow_id: "incident_analysis",
    workflow_instance_id: activeWorkflow.id,
    last_completed_step: activeWorkflow.step,
    elapsed_seconds: Math.floor((Date.now() - activeWorkflow.startedAt) / 1000),
    completion_state: completionState,
  });
  activeWorkflow = null;
  clearTimeout(abandonmentTimer);
}

function trackFrontendError(errorName, severity) {
  track("frontend_error_captured", {
    error_fingerprint: fingerprintError(errorName),
    component_area: "shared",
    severity,
    release: "backoffice-static-v1",
    occurrence_count_bucket: "1",
  });
}

function fingerprintError(errorName) {
  let first = 2166136261;
  let second = 0x9e3779b9;
  for (const character of String(errorName)) {
    first = Math.imul(first ^ character.charCodeAt(0), 16777619);
    second = Math.imul(second ^ character.charCodeAt(0), 2246822519);
  }
  return `${(first >>> 0).toString(16).padStart(8, "0")}${(second >>> 0).toString(16).padStart(8, "0")}`;
}

function createUuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    return (character === "x" ? random : (random & 0x3) | 0x8).toString(16);
  });
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
  if (!activeWorkflow) startIncidentWorkflow({ currentTarget: fileInput });
  activeWorkflow.step = "submit";
  clearTimeout(abandonmentTimer);
  abandonmentTimer = setTimeout(() => abandonIncidentWorkflow("inactive_timeout"), 30 * 60 * 1000);

  status.textContent = "Analizando...";
  result.innerHTML = "";
  download.classList.add("is-disabled");
  download.setAttribute("aria-disabled", "true");
  const requestId = createUuid();
  const requestStartedAt = performance.now();
  window.__BRASALAND_ACTIVE_REQUEST_ID__ = requestId;
  let response;
  let failureTracked = false;
  try {
    const formData = new FormData();
    formData.append("file", file);
    response = await fetch(`${apiBase}/api/incidents/analyze`, {
      method: "POST",
      body: formData,
      headers: { "X-Request-ID": requestId },
    });
    const durationMs = performance.now() - requestStartedAt;
    track("api_latency_recorded", {
      route_template: "/api/incidents/analyze",
      http_method: "POST",
      status_code: response.status,
      duration_ms: durationMs,
      sample_rate: 1,
      service_name: "incident-analysis-api",
    });
    const payload = await response.json();
    if (!response.ok) {
      trackApiFailure(response.status);
      trackIncidentFailure(response.status, file.size, durationMs);
      failureTracked = true;
      throw new Error(payload.error || "No se pudo analizar el fichero.");
    }
    status.textContent = "Análisis completado.";
    result.innerHTML = renderAnalysis(payload);
    download.href = `${apiBase}/api/incidents/results/export`;
    download.classList.remove("is-disabled");
    download.removeAttribute("aria-disabled");
    track("incident_analysis_completed", {
      total_records: payload.total_records,
      valid_records: payload.valid_records,
      invalid_records: payload.invalid_records,
      duration_ms: durationMs,
      file_size_bytes: file.size,
    });
    completeIncidentWorkflow();
  } catch (error) {
    if (!failureTracked) {
      const durationMs = performance.now() - requestStartedAt;
      if (!response) {
        track("api_latency_recorded", {
          route_template: "/api/incidents/analyze",
          http_method: "POST",
          status_code: 503,
          duration_ms: durationMs,
          sample_rate: 1,
          service_name: "incident-analysis-api",
        });
        trackApiFailure(503);
      }
      trackIncidentFailure(response?.status || 0, file.size, durationMs);
    }
    status.textContent = error.message;
    result.innerHTML = "";
  } finally {
    delete window.__BRASALAND_ACTIVE_REQUEST_ID__;
  }
}

function trackApiFailure(statusCode) {
  const code = statusCode === 401 ? "unauthorized"
    : statusCode === 403 ? "forbidden"
      : statusCode === 404 ? "not_found"
        : statusCode === 429 ? "rate_limited"
          : statusCode >= 500 ? "server_error"
            : statusCode >= 400 ? "validation_error" : "dependency_error";
  track("api_request_failed", {
    route_template: "/api/incidents/analyze",
    http_method: "POST",
    status_code: statusCode >= 400 ? statusCode : 503,
    error_code: code,
    retryable: statusCode === 0 || statusCode === 429 || statusCode >= 500,
    service_name: "incident-analysis-api",
  });
}

function trackIncidentFailure(statusCode, fileSizeBytes, durationMs) {
  const isValidation = statusCode >= 400 && statusCode < 500;
  track("incident_analysis_failed", {
    failure_stage: statusCode === 0 || statusCode >= 500 ? "dependency" : isValidation ? "validation" : "analysis",
    error_code: statusCode === 415 ? "unsupported_file"
      : statusCode === 413 ? "file_too_large"
        : statusCode === 400 ? "malformed_csv"
          : statusCode === 0 || statusCode >= 500 ? "analysis_unavailable" : "internal_error",
    file_size_bytes: fileSizeBytes,
    duration_ms: durationMs,
  });
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
