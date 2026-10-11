import { loadPublicConfig } from "./runtime-config.mjs";

const config = await loadPublicConfig();
const reportUrl = (
  config.NEXT_PUBLIC_TELEMETRY_REPORT_ENDPOINT
  || (config.NEXT_PUBLIC_TELEMETRY_ENDPOINT || "http://127.0.0.1:8000/telemetry/events").replace(/\/events\/?$/, "/report")
).replace(/\/$/, "");
const form = document.querySelector("#period-form");
const startInput = document.querySelector("#start-date");
const endInput = document.querySelector("#end-date");
const status = document.querySelector("#telemetry-status");
const period = document.querySelector("#report-period");
const loadButton = document.querySelector("#load-report");
const retryButton = document.querySelector("#retry-report");

form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadReport();
});
retryButton.addEventListener("click", loadReport);
loadReport();

async function loadReport() {
  status.textContent = "Cargando métricas técnicas...";
  status.classList.remove("is-error");
  retryButton.hidden = true;
  loadButton.disabled = true;
  period.textContent = "";
  clearTables();

  const parameters = new URLSearchParams();
  if (startInput.value) parameters.set("start_date", asUtcIso(startInput.value));
  if (endInput.value) parameters.set("end_date", asUtcIso(endInput.value));
  if (startInput.value && endInput.value && new Date(startInput.value) >= new Date(endInput.value)) {
    showError("La fecha inicial debe ser anterior a la fecha final.");
    return;
  }

  try {
    const query = parameters.size ? `?${parameters}` : "";
    const response = await fetch(`${reportUrl}${query}`, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      if (response.status === 503) throw new Error("El almacenamiento de telemetría no está disponible o no está configurado.");
      if (response.status === 400) throw new Error("Revisa que las fechas incluyan zona horaria UTC y formen un intervalo válido.");
      throw new Error("No se pudo cargar el reporte técnico. Inténtalo de nuevo.");
    }
    const report = await response.json();
    period.textContent = `Período UTC: ${formatDateTime(report.period.from)} — ${formatDateTime(report.period.to)} (fin exclusivo)`;
    renderTable("events-rows", report.metrics.events_per_day, [
      ["event_date", formatDate], ["event_type", String], ["event_count", formatCount],
    ]);
    renderTable("errors-rows", report.metrics.error_rate_by_type, [
      ["event_date", formatDate], ["event_type", String], ["error_events", formatCount],
      ["total_events", formatCount], ["error_rate", formatPercent],
    ]);
    renderTable("latency-rows", report.metrics.latency_by_day, [
      ["event_date", formatDate], ["route_template", String], ["request_count", formatCount],
      ["mean_latency_ms", formatDecimal], ["p95_latency_ms", formatDecimal],
    ]);
    renderTable("auth-rows", report.metrics.auth_failure_rate, [
      ["event_date", formatDate], ["failed_attempts", formatCount],
      ["login_attempts", formatCount], ["failure_rate", formatPercent],
    ]);
    const rowCount = Object.values(report.metrics).reduce((total, rows) => total + rows.length, 0);
    status.textContent = rowCount ? "Reporte técnico actualizado." : "No hay eventos para el período seleccionado.";
  } catch (error) {
    showError(error.message);
  } finally {
    loadButton.disabled = false;
  }
}

function renderTable(bodyId, rows, columns) {
  const body = document.getElementById(bodyId);
  if (!rows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = columns.length;
    cell.textContent = "Sin eventos en el período.";
    row.append(cell);
    body.append(row);
    return;
  }
  for (const record of rows) {
    const row = document.createElement("tr");
    for (const [key, formatter] of columns) {
      const cell = document.createElement("td");
      cell.textContent = formatter(record[key]);
      row.append(cell);
    }
    body.append(row);
  }
}

function clearTables() {
  for (const id of ["events-rows", "errors-rows", "latency-rows", "auth-rows"]) {
    document.getElementById(id).replaceChildren();
  }
}

function showError(message) {
  status.textContent = message;
  status.classList.add("is-error");
  retryButton.hidden = false;
  loadButton.disabled = false;
}

function asUtcIso(value) {
  const utcValue = value.length === 16 ? `${value}:00` : value;
  return `${utcValue}Z`;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeZone: "UTC" })
    .format(new Date(`${value}T00:00:00Z`));
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" })
    .format(new Date(value));
}

function formatCount(value) {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 }).format(value);
}

function formatDecimal(value) {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 }).format(value);
}

function formatPercent(value) {
  return new Intl.NumberFormat("es-CO", { style: "percent", maximumFractionDigits: 2 }).format(value);
}
