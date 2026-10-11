import { loadPublicConfig } from "./runtime-config.mjs";

const runtimeConfig = await loadPublicConfig();
const reportingApiBase = (runtimeConfig.NEXT_PUBLIC_REPORTING_API_ENDPOINT || "http://127.0.0.1:8000").replace(/\/$/, "");
const tokenKey = "brasaland_access_token";
const loginForm = document.querySelector("#login-form");
const reportSection = document.querySelector("#weekly-report");
const reportStatus = document.querySelector("#report-status");
const reportRows = document.querySelector("#report-rows");
const weekInput = document.querySelector("#week-start");
const logoutButton = document.querySelector("#logout-button");

loginForm.addEventListener("submit", login);
document.querySelector("#load-report").addEventListener("click", loadReport);
logoutButton.addEventListener("click", logout);

if (localStorage.getItem(tokenKey)) {
  showReport();
  await loadReport();
}

async function login(event) {
  event.preventDefault();
  setStatus("Validando acceso...");
  const credentials = new URLSearchParams(new FormData(loginForm));
  try {
    const response = await fetch(`${reportingApiBase}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: credentials,
    });
    if (!response.ok) throw new Error("No se pudo iniciar sesión. Revisa tu correo y contraseña.");
    const { access_token: accessToken } = await response.json();
    localStorage.setItem(tokenKey, accessToken);
    loginForm.reset();
    showReport();
    await loadReport();
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadReport() {
  const token = localStorage.getItem(tokenKey);
  if (!token) {
    showLogin();
    setStatus("Inicia sesión para consultar el reporte.");
    return;
  }

  setStatus("Cargando datos semanales...");
  reportRows.replaceChildren();
  if (weekInput.value && new Date(`${weekInput.value}T00:00:00Z`).getUTCDay() !== 1) {
    setStatus("Selecciona un lunes para consultar el reporte semanal.", true);
    return;
  }
  const params = new URLSearchParams();
  if (weekInput.value) params.set("week_start", weekInput.value);

  try {
    const query = params.size ? `?${params}` : "";
    const response = await fetch(`${reportingApiBase}/reporting/weekly-location-performance${query}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (response.status === 401) {
      localStorage.removeItem(tokenKey);
      showLogin();
      throw new Error("Tu sesión venció. Inicia sesión de nuevo.");
    }
    if (response.status === 404) throw new Error("No hay datos publicados para esa semana.");
    if (!response.ok) throw new Error("No se pudo cargar el reporte. Inténtalo de nuevo.");

    const report = await response.json();
    weekInput.value = report.week_start;
    document.querySelector("#report-title").textContent = `Semana del ${formatDate(report.week_start)} al ${formatDate(addDays(report.week_start, 6))}`;
    renderRows(report.locations);
    setStatus(report.locations.length ? `${report.locations.length} locales incluidos` : "No hay locales para esta semana.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

function renderRows(locations) {
  reportRows.innerHTML = locations.map((location) => `
    <tr>
      <td>${escapeHtml(location.location_id)}<small>${location.currency}</small></td>
      <td>${location.country === "CO" ? "Colombia" : "Estados Unidos"}</td>
      <td>${formatCurrency(location.total_purchase_cost, location.currency)}</td>
      <td>${formatCurrency(location.total_waste_cost, location.currency)}</td>
      <td>${new Intl.NumberFormat("es-CO", { style: "percent", maximumFractionDigits: 2 }).format(location.waste_ratio)}</td>
      <td>${formatCount(location.stockout_events_count)}</td>
      <td>${formatCount(location.price_alert_events_count)}</td>
    </tr>
  `).join("");
}

function formatCurrency(value, currency) {
  return new Intl.NumberFormat(currency === "COP" ? "es-CO" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatCount(value) {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 }).format(value);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "long", timeZone: "UTC" })
    .format(new Date(`${value}T00:00:00Z`));
}

function addDays(value, days) {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function showReport() {
  loginForm.hidden = true;
  reportSection.hidden = false;
  logoutButton.hidden = false;
}

function showLogin() {
  loginForm.hidden = false;
  reportSection.hidden = true;
  logoutButton.hidden = true;
}

function logout() {
  localStorage.removeItem(tokenKey);
  weekInput.value = "";
  reportRows.replaceChildren();
  document.querySelector("#report-title").textContent = "";
  showLogin();
  setStatus("Sesión cerrada.");
}

function setStatus(message, isError = false) {
  reportStatus.textContent = message;
  reportStatus.classList.toggle("is-error", isError);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[character]));
}