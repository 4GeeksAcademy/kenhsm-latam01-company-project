import { loadPublicConfig } from "./runtime-config.mjs";

const config = await loadPublicConfig();
const apiBase = (config.NEXT_PUBLIC_REPORTING_API_ENDPOINT || "http://127.0.0.1:8000").replace(/\/$/, "");
const tokenKey = "brasaland_access_token";
const sessionStorageKey = "brasaland_manager_support_session_id";
const locationStorageKey = "brasaland_manager_support_location_id";
const loginForm = document.querySelector("#login-form");
const chatApp = document.querySelector("#chat-app");
const connectionStatus = document.querySelector("#connection-status");
const locationSelect = document.querySelector("#location-id");
const messagesElement = document.querySelector("#chat-messages");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-button");
const connectButton = document.querySelector("#connect-button");
const newSessionButton = document.querySelector("#new-session-button");
const logoutButton = document.querySelector("#logout-button");

let socket = null;
let sessionId = sessionStorage.getItem(sessionStorageKey) || "";
let reconnectTimer = null;
let reconnectDelay = 500;
let lastEventSequence = 0;
let rehydrated = false;
let generating = false;
let interruptPending = false;
let reconnectEnabled = true;
const renderedMessages = new Map();

loginForm.addEventListener("submit", login);
chatForm.addEventListener("submit", sendMessage);
connectButton.addEventListener("click", () => connect(true));
newSessionButton.addEventListener("click", startNewSession);
logoutButton.addEventListener("click", logout);

const savedLocation = sessionStorage.getItem(locationStorageKey);
if (savedLocation) locationSelect.value = savedLocation;
if (localStorage.getItem(tokenKey)) {
  showChat();
  if (sessionId && savedLocation) connect(false);
} else {
  showLogin();
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
    if (!response.ok) throw new Error("No se pudo iniciar sesión. Revisa tu correo y contraseña.");
    const { access_token: accessToken } = await response.json();
    localStorage.setItem(tokenKey, accessToken);
    loginForm.reset();
    showChat();
    setStatus("Selecciona tu local y conecta la conversación.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

function connect(createSession) {
  const token = localStorage.getItem(tokenKey);
  const locationId = locationSelect.value;
  if (!token) return showLogin();
  if (!locationId) {
    setStatus("Selecciona un local antes de conectar.", true);
    return;
  }
  if (createSession || !sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(sessionStorageKey, sessionId);
    sessionStorage.setItem(locationStorageKey, locationId);
    clearMessages();
    lastEventSequence = 0;
  }
  reconnectEnabled = true;
  clearTimeout(reconnectTimer);
  socket?.close();
  rehydrated = false;
  setComposerState();
  setStatus("Conectando y recuperando conversación...");
  const wsBase = apiBase.replace(/^http/, "ws");
  const query = new URLSearchParams({ token, location_id: locationId });
  const candidate = new WebSocket(`${wsBase}/agent/chat/${encodeURIComponent(sessionId)}?${query}`);
  socket = candidate;

  candidate.addEventListener("open", () => {
    if (socket === candidate) setStatus("Socket conectado; esperando el historial...");
  });
  candidate.addEventListener("message", (messageEvent) => {
    if (socket !== candidate) return;
    try {
      handleEvent(JSON.parse(messageEvent.data));
    } catch {
      setStatus("El servidor envió un evento inválido.", true);
    }
  });
  candidate.addEventListener("error", () => {
    if (socket === candidate) setStatus("Conexión interrumpida; intentando recuperar el hilo...", true);
  });
  candidate.addEventListener("close", (closeEvent) => {
    if (socket !== candidate) return;
    socket = null;
    rehydrated = false;
    setComposerState();
    if (closeEvent.code === 4401) {
      localStorage.removeItem(tokenKey);
      showLogin();
      setStatus("La sesión expiró. Inicia sesión nuevamente.", true);
      return;
    }
    if (reconnectEnabled) scheduleReconnect();
  });
}

function handleEvent(frame) {
  const { event, data = {} } = frame || {};
  if (event === "session_snapshot") {
    if (data.session_id !== sessionId) return;
    lastEventSequence = Number(data.event_sequence || 0);
    sessionStorage.setItem(locationStorageKey, data.location_id);
    locationSelect.value = data.location_id;
    locationSelect.disabled = true;
    renderSnapshot(data.messages || []);
    rehydrated = true;
    generating = (data.messages || []).some((message) => message.status === "generating");
    interruptPending = false;
    reconnectDelay = 500;
    setStatus("Conectado · historial restaurado");
    setComposerState();
    return;
  }
  if (data.session_id !== sessionId) return;
  const eventSequence = Number(data.event_sequence || 0);
  if (eventSequence && eventSequence <= lastEventSequence) return;
  if (eventSequence) lastEventSequence = eventSequence;

  if (event === "user_message") {
    upsertMessage({ ...data, role: "user", status: "completed" });
  } else if (event === "generation_started") {
    interruptPending = false;
    generating = true;
    upsertMessage({ message_id: data.message_id, role: "assistant", text: "", status: "generating" });
  } else if (event === "token_chunk") {
    const existing = renderedMessages.get(data.message_id);
    if (!existing) upsertMessage({ message_id: data.message_id, role: "assistant", text: data.token, status: "generating" });
    else appendToMessage(data.message_id, data.token);
  } else if (event === "generation_interrupted") {
    updateMessageStatus(data.message_id, "interrupted");
    generating = interruptPending;
  } else if (event === "generation_completed") {
    updateMessageStatus(data.message_id, "completed");
    generating = false;
  } else if (event === "generation_failed") {
    updateMessageStatus(data.message_id, "failed");
    generating = false;
    setStatus("La respuesta no pudo completarse. Puedes enviar otro mensaje.", true);
  } else if (event === "chat_error") {
    setStatus(data.detail || "No se pudo procesar el mensaje.", true);
  } else if (event === "session_closed") {
    generating = false;
    rehydrated = false;
    setStatus("Conversación cerrada.");
  }
  setComposerState();
}

function sendMessage(event) {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text || !socket || socket.readyState !== WebSocket.OPEN || !rehydrated) return;
  const frame = generating
    ? { event: "interrupt_requested", data: { session_id: sessionId, new_input: text } }
    : { event: "user_message", data: { session_id: sessionId, text } };
  socket.send(JSON.stringify(frame));
  if (generating) interruptPending = true;
  chatInput.value = "";
  setComposerState();
  chatInput.focus();
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  setStatus(`Reconectando en ${Math.ceil(reconnectDelay / 1000)} s; se restaurará el historial...`, true);
  reconnectTimer = setTimeout(() => {
    if (reconnectEnabled && localStorage.getItem(tokenKey)) connect(false);
  }, reconnectDelay);
  reconnectDelay = Math.min(reconnectDelay * 2, 30000);
}

function startNewSession() {
  reconnectEnabled = false;
  socket?.close(1000, "new session");
  socket = null;
  clearTimeout(reconnectTimer);
  sessionStorage.removeItem(sessionStorageKey);
  sessionStorage.removeItem(locationStorageKey);
  locationSelect.disabled = false;
  sessionId = "";
  lastEventSequence = 0;
  generating = false;
  interruptPending = false;
  rehydrated = false;
  clearMessages();
  setStatus("Selecciona el local para iniciar otra conversación.");
  setComposerState();
}

function logout() {
  reconnectEnabled = false;
  clearTimeout(reconnectTimer);
  socket?.close(1000, "logout");
  socket = null;
  localStorage.removeItem(tokenKey);
  showLogin();
}

function renderSnapshot(messages) {
  clearMessages();
  for (const message of messages) upsertMessage(message);
}

function upsertMessage(message) {
  if (!message.message_id) return;
  let entry = renderedMessages.get(message.message_id);
  if (!entry) {
    const item = document.createElement("li");
    item.className = "chat-message";
    item.dataset.role = message.role;
    item.dataset.status = message.status || "completed";
    const body = document.createElement("p");
    const status = document.createElement("small");
    item.append(body, status);
    messagesElement.append(item);
    entry = { item, body, status };
    renderedMessages.set(message.message_id, entry);
  }
  if (message.text !== undefined) entry.body.textContent = message.text;
  updateMessageStatus(message.message_id, message.status || "completed");
  scrollToLatest();
}

function appendToMessage(messageId, token) {
  const entry = renderedMessages.get(messageId);
  if (!entry) return;
  entry.body.textContent += token;
  scrollToLatest();
}

function updateMessageStatus(messageId, status) {
  const entry = renderedMessages.get(messageId);
  if (!entry) return;
  entry.item.dataset.status = status;
  entry.status.textContent = ({
    generating: "Respondiendo…",
    interrupted: "Interrumpido",
    completed: "",
    failed: "No completado",
  })[status] || status;
}

function clearMessages() {
  renderedMessages.clear();
  messagesElement.replaceChildren();
}

function scrollToLatest() {
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function setComposerState() {
  sendButton.disabled = !rehydrated || !socket || socket.readyState !== WebSocket.OPEN || interruptPending;
  sendButton.textContent = interruptPending ? "Redirigiendo…" : generating ? "Interrumpir y redirigir" : "Enviar";
}

function setStatus(message, isError = false) {
  connectionStatus.textContent = message;
  connectionStatus.dataset.state = isError ? "error" : "ok";
}

function showChat() {
  loginForm.hidden = true;
  chatApp.hidden = false;
  logoutButton.hidden = false;
}

function showLogin() {
  loginForm.hidden = false;
  chatApp.hidden = true;
  logoutButton.hidden = true;
}