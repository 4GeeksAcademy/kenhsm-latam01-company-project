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
const statusLabels = {
  analizando: "Analizando", descartado: "Descartado", analisis_completo: "Análisis completo",
  generando_borrador: "Generando borradores", "en_evaluación": "En evaluación",
  needs_human_review: "Revisión requerida", "esperando_aprobación": "Esperando aprobación", terminado: "Terminado",
};
const approvers = { marketing: "Camila Ospina", operaciones: "Felipe Guerrero", procurement: "Lucía Fernández", training: "Jake Morrison", ceo: "Mariana Restrepo" };
let selectedTicketId = null;
let refreshTimer = null;
let currentUserName = "";

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
ticketDetail.addEventListener("click", (event) => {
  if (event.target.closest("[data-generate-draft]")) generateDraft();
});
ticketDetail.addEventListener("submit", submitApproval);

if (localStorage.getItem(tokenKey)) {
  showWorkspace();
  await loadCurrentUser();
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
    await loadCurrentUser();
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
    if (tickets.some((ticket) => ["analizando", "generando_borrador", "en_evaluación", "esperando_aprobación"].includes(ticket.status))) {
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
  const approvalsByKey = Object.fromEntries((ticket.approvals || []).map((approval) => [approval.approval_key, approval]));
  const conflicts = ticket.handoff_payload?.approval_workflow?.conflicts || [];
  const scope = Array.isArray(metadata.scope) ? metadata.scope.join(" ") : metadata.scope;
  const metrics = metadata.readability_metrics || {};
  const metricSummary = metrics.word_count == null ? "No disponible" : `${formatNumber(metrics.word_count)} palabras · ~${formatNumber(metrics.estimated_input_tokens)} tokens`;
  const questions = metadata.open_questions || [];
  const sectionsMarkup = sections.map((section) => renderDepartment(section, approvalsByKey[section.department_id], conflicts)).join("") || '<p class="detail-empty">Los aspectos por departamento estarán disponibles al completar el análisis.</p>';
  const ceoMarkup = approvalsByKey.ceo ? renderApprovalCard("ceo", approvalsByKey.ceo, "Aprobación ejecutiva", conflicts.filter((item) => item.trigger_id === "ceo-threshold")) : "";
  const arbitrationMarkup = conflicts.length ? `<section class="arbitration-summary"><h4>Arbitraje requerido</h4><ul>${conflicts.map((item) => `<li><strong>${escapeHtml(item.trigger_id)}</strong> · Árbitro: ${escapeHtml(item.owner)} · ${escapeHtml(item.resolution)}</li>`).join("")}</ul></section>` : "";
  const finalDocument = ticket.final_document ? `<section class="final-document"><h4>Documento final</h4><p>Generado ${escapeHtml(formatDate(ticket.final_document.generated_at))}</p><pre>${escapeHtml(ticket.final_document.document_markdown)}</pre><a href="${apiBase}/rfp-intake/${encodeURIComponent(ticket.ticket_id)}/final-document" target="_blank" rel="noreferrer">Abrir documento final</a></section>` : "";
  const traceMarkup = (ticket.execution_trace || []).length ? `<details class="execution-trace"><summary>Trazabilidad (${ticket.execution_trace.length})</summary><ol>${ticket.execution_trace.map((event) => `<li><strong>${escapeHtml(event.agent)}</strong><time>${escapeHtml(formatDate(event.timestamp))}</time><pre>Entrada: ${escapeHtml(JSON.stringify(event.input))}\nSalida: ${escapeHtml(JSON.stringify(event.output))}</pre></li>`).join("")}</ol></details>` : "";
  const draftAction = ["analisis_completo", "needs_human_review"].includes(ticket.status)
    ? `<button class="secondary-button rfp-draft-action" type="button" data-generate-draft>${ticket.status === "needs_human_review" ? "Reabrir generación" : "Generar propuesta"}</button>`
    : "";
  const draftStatus = ticket.handoff_payload?.draft_generation?.status;
  const handoffNote = ticket.handoff_payload ? draftStatus
    ? `<p class="handoff-note">Estado de generación: ${escapeHtml(draftStatus)}.</p>`
    : '<p class="handoff-note">Análisis de Parte 1 listo; el handoff conserva los metadatos y workstreams para generar la propuesta.</p>'
    : "";
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
    ${arbitrationMarkup}<h4>Workstreams y aprobaciones</h4><div class="department-list">${sectionsMarkup}${ceoMarkup}</div>
    ${handoffNote}${draftAction}
    ${finalDocument}${traceMarkup}
  `;
}

function renderDepartment(section, approval, conflicts = []) {
  const aspects = section.key_aspects || {};
  const extracts = aspects.source_extracts || [];
  const questions = aspects.open_questions || [];
  const status = approval?.approval_status || section.approval_status || "pendiente";
  const approver = approvers[section.department_id];
  const departmentConflicts = conflicts.filter((item) => item.departments.includes(section.department_id));
  const draft = section.draft_content ? `<details class="draft-preview" open><summary>Borrador</summary><pre>${escapeHtml(section.draft_content)}</pre></details>` : "";
  const evaluation = section.evaluation_results ? `<p class="evaluation-summary">Evaluación automática: ${section.evaluation_results.overall_pass ? "apta" : "requiere revisión"}</p>` : "";
  return `<article class="department-item"><header><h5>${escapeHtml(aspects.department_name || section.department_id)}</h5><span>${escapeHtml(aspects.contact || approver || "")}</span><span class="approval-state" data-approval="${escapeHtml(status)}">${escapeHtml(status)}</span></header><p>${escapeHtml(aspects.focus || "")}</p>${extracts.map((excerpt) => `<blockquote>${escapeHtml(excerpt)}</blockquote>`).join("")}${questions.length ? `<ul>${questions.map((question) => `<li>Confirmar ${escapeHtml(questionLabel(question).toLowerCase())}</li>`).join("")}</ul>` : ""}${draft}${evaluation}${renderApprovalCard(section.department_id, approval, "Sign-off", departmentConflicts, section)}</article>`;
}

function renderApprovalCard(approvalKey, approval, heading, conflicts = [], section = {}) {
  if (!approval) return "";
  const status = approval.approval_status || "pendiente";
  if (status !== "pendiente") return `<p class="approval-note">${escapeHtml(heading)}: ${escapeHtml(status)} · ${escapeHtml(approval.approver || approvers[approvalKey])}${approval.comment ? ` · ${escapeHtml(approval.comment)}` : ""}</p>`;
  const expected = approvers[approvalKey];
  const isApprover = normalizeName(currentUserName) === normalizeName(expected);
  const conflictMarkup = conflicts.map((item) => `<p class="arbitration-note">${escapeHtml(item.trigger_id)}: ${escapeHtml(item.resolution)}</p>`).join("");
  const approvalBlocked = conflicts.some((item) => item.trigger_id !== "ceo-threshold");
  const terms = section.evaluation_results?.commercial_terms || {};
  const commercialFields = approvalKey === "operaciones"
    ? `<label>Precio por evento (USD)<input type="number" name="price_per_event_usd" min="0" step="0.01" value="${escapeHtml(terms.price_per_event_usd ?? "")}" /></label>`
    : approvalKey === "procurement"
      ? `<label>Costo por evento (USD)<input type="number" name="cost_per_event_usd" min="0" step="0.01" value="${escapeHtml(terms.cost_per_event_usd ?? "")}" /></label>`
      : "";
  const setupField = approvalKey !== "ceo" ? `<label>Montaje/entrega (días hábiles)<input type="number" name="setup_lead_time_business_days" min="0" step="1" value="${escapeHtml(terms.setup_lead_time_business_days ?? "")}" /></label>` : "";
  const form = isApprover ? `<form class="approval-form" data-approval-key="${escapeHtml(approvalKey)}"><label>Decisión<select name="action"><option value="approve" ${approvalBlocked ? "disabled" : ""}>Aprobar</option><option value="request_changes">Solicitar cambios</option><option value="reject">Rechazar</option></select></label>${commercialFields}${setupField}<label>Comentario<textarea name="comment" rows="2" maxlength="2000" placeholder="Obligatorio al solicitar cambios"></textarea></label><button type="submit">Registrar decisión</button></form>` : `<p class="approval-note">Pendiente de ${escapeHtml(expected)}. Inicia sesión con el perfil correspondiente para registrar la decisión.</p>`;
  return `<section class="approval-card"><h5>${escapeHtml(heading)} · ${escapeHtml(expected)}</h5>${conflictMarkup}${form}</section>`;
}

async function submitApproval(event) {
  const form = event.target.closest(".approval-form");
  if (!form) return;
  event.preventDefault();
  const approvalKey = form.dataset.approvalKey;
  const values = new FormData(form);
  const payload = { action: values.get("action"), comment: String(values.get("comment") || "").trim() };
  for (const key of ["price_per_event_usd", "cost_per_event_usd", "setup_lead_time_business_days"]) {
    const value = values.get(key);
    if (value !== null && value !== "") payload[key] = Number(value);
  }
  if (payload.action === "request_changes" && !payload.comment) {
    setStatus("Describe los cambios solicitados antes de continuar.", true);
    return;
  }
  const submitButton = form.querySelector("button[type=submit]");
  submitButton.disabled = true;
  try {
    const response = await request(`${apiBase}/rfp-intake/${encodeURIComponent(selectedTicketId)}/approvals/${encodeURIComponent(approvalKey)}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    if (!response.ok) throw await responseError(response, "No se pudo registrar la aprobación.");
    const result = await response.json();
    setStatus(`Decisión registrada. Estado del ticket: ${statusLabels[result.status] || result.status}.`);
    await loadTicket(selectedTicketId);
  } catch (error) {
    setStatus(error.message, true);
    submitButton.disabled = false;
  }
}

async function generateDraft() {
  const button = ticketDetail.querySelector("[data-generate-draft]");
  if (!button || !selectedTicketId) return;
  button.disabled = true;
  setStatus("Generando y evaluando las secciones por departamento...");
  try {
    const response = await request(`${apiBase}/rfp-intake/${encodeURIComponent(selectedTicketId)}/generate-draft`, { method: "POST" });
    if (!response.ok) throw await responseError(response, "No se pudo iniciar la generación.");
    setStatus("La generación de borradores continúa en segundo plano.");
    await loadTickets();
  } catch (error) {
    setStatus(error.message, true);
    button.disabled = false;
  }
}

async function loadCurrentUser() {
  try {
    const response = await request(`${apiBase}/auth/me`);
    if (!response.ok) throw new Error("No se pudo consultar el perfil.");
    const user = await response.json();
    currentUserName = user.profile?.name || "";
  } catch {
    currentUserName = "";
  }
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
  const payload = await response.json().catch(() => ({}));
  return new Error(payload.detail || fallback);
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

function normalizeName(value) {
  return String(value || "").trim().replace(/\s+/g, " ").toLocaleLowerCase("es");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character]));
}

function setStatus(message, isError = false) {
  pageStatus.textContent = message;
  pageStatus.classList.toggle("is-error", isError);
}