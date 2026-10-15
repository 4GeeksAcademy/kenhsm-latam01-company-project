import { loadPublicConfig } from "./runtime-config.mjs";

const config = await loadPublicConfig();
const apiBase = (config.NEXT_PUBLIC_RFP_API_ENDPOINT || config.NEXT_PUBLIC_REPORTING_API_ENDPOINT || "http://127.0.0.1:8000").replace(/\/$/, "");
const tokenKey = "brasaland_access_token";
const loginForm = document.querySelector("#login-form");
const workspace = document.querySelector("#rfp-workspace");
const pageStatus = document.querySelector("#page-status");
const ticketList = document.querySelector("#ticket-list");
const ticketDetail = document.querySelector("#ticket-detail");
const logoutButton = document.querySelector("#logout-button");
const uploadForm = document.querySelector("#upload-form");
const uploadButton = document.querySelector("#upload-button");
const statusLabels = { analizando: "Analizando", descartado: "Descartado", analisis_completo: "Análisis completo" };
let selectedTicketId = null;
let refreshTimer = null;

loginForm.addEventListener("submit", login);
uploadForm.addEventListener("submit", submitRfp);
logoutButton.addEventListener("click", logout);
document.querySelector("#refresh-button").addEventListener("click", loadTickets);
ticketList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-ticket-id]");
  if (!button) return;
  selectedTicketId = button.dataset.ticketId;
  loadTicket(selectedTicketId);
  markSelectedTicket();
});

if (localStorage.getItem(tokenKey)) {
  showWorkspace();
  await loadTickets();
  refreshTimer = setInterval(loadTickets, 5000);
}

async function login(event) {
  event.preventDefault();
  setStatus("Validando acceso...");
  try {
    const response = await fetch(`${apiBase}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(new FormData(loginForm)),
    });
    if (!response.ok) throw new Error("No se pudo iniciar sesión. Revisa tus credenciales.");
    const { access_token: token } = await response.json();
    localStorage.setItem(tokenKey, token);
    loginForm.reset();
    showWorkspace();
    await loadTickets();
    refreshTimer = setInterval(loadTickets, 5000);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function submitRfp(event) {
  event.preventDefault();
  const file = document.querySelector("#rfp-file").files[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf") || file.size > 25 * 1024 * 1024) {
    setStatus("Selecciona un PDF de hasta 25 MB.", true);
    return;
  }
  const body = new FormData();
  body.append("file", file);
  uploadButton.disabled = true;
  setStatus("Guardando el documento y creando el ticket...");
  try {
    const response = await request(`${apiBase}/rfp-intake`, { method: "POST", body });
    if (!response.ok) throw await responseError(response, "No se pudo recibir el PDF.");
    const ticket = await response.json();
    selectedTicketId = ticket.ticket_id;
    uploadForm.reset();
    setStatus(`Ticket ${ticket.ticket_id} creado. El análisis continúa en segundo plano.`);
    await loadTickets();
    await loadTicket(selectedTicketId);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    uploadButton.disabled = false;
  }
}

async function loadTickets() {
  if (!localStorage.getItem(tokenKey)) return;
  try {
    const response = await request(`${apiBase}/rfp-intake`);
    if (!response.ok) throw await responseError(response, "No se pudieron cargar los tickets.");
    const tickets = await response.json();
    renderTicketList(tickets);
    if (!selectedTicketId && tickets.length) selectedTicketId = tickets[0].ticket_id;
    if (selectedTicketId) await loadTicket(selectedTicketId);
    else ticketDetail.innerHTML = '<p class="detail-empty">Aún no hay tickets. Sube una RFP para iniciar.</p>';
    if (tickets.some((ticket) => ticket.status === "analizando")) {
      setStatus("Actualización automática cada 5 segundos.");
    }
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadTicket(ticketId) {
  try {
    const response = await request(`${apiBase}/rfp-intake/${encodeURIComponent(ticketId)}`);
    if (!response.ok) throw await responseError(response, "No se pudo consultar el ticket.");
    renderTicket(await response.json());
    markSelectedTicket();
  } catch (error) {
    setStatus(error.message, true);
  }
}

function renderTicketList(tickets) {
  ticketList.replaceChildren();
  if (!tickets.length) {
    ticketList.innerHTML = '<p class="queue-empty">Sin tickets recibidos.</p>';
    return;
  }
  for (const ticket of tickets) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ticket-select";
    button.dataset.ticketId = ticket.ticket_id;
    button.innerHTML = `<strong>${escapeHtml(ticket.ticket_id)}</strong><span class="status-badge" data-status="${escapeHtml(ticket.status)}">${escapeHtml(statusLabels[ticket.status] || ticket.status)}</span><small>${escapeHtml(formatDate(ticket.created_at))}</small>`;
    ticketList.append(button);
  }
  markSelectedTicket();
}

function renderTicket(ticket) {
  const metadata = ticket.metadata || {};
  const client = metadata.client_name || "Cliente por identificar";
  const status = statusLabels[ticket.status] || ticket.status;
  const sections = ticket.department_sections || [];
  const scope = Array.isArray(metadata.scope) ? metadata.scope.join(" ") : metadata.scope;
  const metrics = metadata.readability_metrics || {};
  const metricSummary = metrics.word_count == null ? "No disponible" : `${formatNumber(metrics.word_count)} palabras · ~${formatNumber(metrics.estimated_input_tokens)} tokens`;
  const questions = metadata.open_questions || [];
  const sectionsMarkup = sections.map((section) => renderDepartment(section)).join("") || '<p class="detail-empty">Los aspectos por departamento estarán disponibles al completar el análisis.</p>';
  ticketDetail.innerHTML = `
    <div class="ticket-title-row"><div><p class="kicker">Expediente ${escapeHtml(ticket.rfp_id || "")}</p><h3 id="detail-title">${escapeHtml(client)}</h3></div><span class="status-badge" data-status="${escapeHtml(ticket.status)}">${escapeHtml(status)}</span></div>
    <p class="detail-meta">Ticket ${escapeHtml(ticket.ticket_id)} · Recibido ${escapeHtml(formatDate(ticket.created_at))}</p>
    ${ticket.processing_error ? `<p class="processing-error" role="alert">${escapeHtml(ticket.processing_error)}</p>` : ""}
    <dl class="metadata-grid">
      ${metadataItem("Ubicación", metadata.location)}${metadataItem("Servicio", metadata.service_type)}
      ${metadataItem("Alcance", scope)}${metadataItem("Fecha límite", metadata.deadline)}
      ${metadataItem("Presupuesto", metadata.budget_range)}${metadataItem("Legibilidad", metricSummary)}
    </dl>
    ${questions.length ? `<h4>Datos por confirmar</h4><ul class="open-questions">${questions.map((question) => `<li>${escapeHtml(questionLabel(question))}</li>`).join("")}</ul>` : ""}
    <h4>Workstreams por departamento</h4><div class="department-list">${sectionsMarkup}</div>
    ${ticket.handoff_payload ? '<p class="handoff-note">Handoff listo para Parte 2: el payload conserva ticket_id, metadatos y workstreams; no requiere volver a leer el PDF.</p>' : ""}
  `;
}

function renderDepartment(section) {
  const aspects = section.key_aspects || {};
  const extracts = aspects.source_extracts || [];
  const questions = aspects.open_questions || [];
  return `<article class="department-item"><header><h5>${escapeHtml(aspects.department_name || section.department_id)}</h5><span>${escapeHtml(aspects.contact || "")}</span></header><p>${escapeHtml(aspects.focus || "")}</p>${extracts.map((excerpt) => `<blockquote>${escapeHtml(excerpt)}</blockquote>`).join("")}${questions.length ? `<ul>${questions.map((question) => `<li>Confirmar ${escapeHtml(questionLabel(question).toLowerCase())}</li>`).join("")}</ul>` : ""}</article>`;
}

function metadataItem(label, value) {
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value || "No identificado")}</dd></div>`;
}

function questionLabel(value) {
  return ({ client_name: "cliente", location: "ubicación", service_type: "tipo de servicio", scope: "alcance", deadline: "fecha límite", budget_range: "rango de presupuesto" })[value] || value;
}

async function request(url, options = {}) {
  const token = localStorage.getItem(tokenKey);
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    logout();
    throw new Error("Tu sesión venció. Inicia sesión de nuevo.");
  }
  return response;
}

async function responseError(response, fallback) {
  if (response.status === 413 || response.status === 415) {
    const payload = await response.json().catch(() => ({}));
    return new Error(payload.detail || fallback);
  }
  return new Error(fallback);
}

function showWorkspace() {
  loginForm.hidden = true;
  workspace.hidden = false;
  logoutButton.hidden = false;
}

function logout() {
  localStorage.removeItem(tokenKey);
  clearInterval(refreshTimer);
  refreshTimer = null;
  selectedTicketId = null;
  workspace.hidden = true;
  loginForm.hidden = false;
  logoutButton.hidden = true;
  ticketList.replaceChildren();
  ticketDetail.innerHTML = '<p class="detail-empty">Inicia sesión para consultar los tickets.</p>';
  setStatus("Sesión cerrada.");
}

function markSelectedTicket() {
  for (const button of ticketList.querySelectorAll("[data-ticket-id]")) {
    button.setAttribute("aria-current", String(button.dataset.ticketId === selectedTicketId));
  }
}

function formatDate(value) {
  if (!value) return "Fecha desconocida";
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function formatNumber(value) {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 }).format(value);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character]));
}

function setStatus(message, isError = false) {
  pageStatus.textContent = message;
  pageStatus.classList.toggle("is-error", isError);
}