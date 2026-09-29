import { loadPublicConfig } from "../../runtime-config.mjs";

const SCHEMA_VERSION = "1.0.0";
const BATCH_INTERVAL_MS = 10_000;
const MAX_BATCH_SIZE = 20;
const MAX_RETRIES = 3;
const RETRY_BASE_MS = 500;
const SESSION_ID = createUuid();
const PSEUDONYMOUS_USER_ID = getPseudonymousUserId();

const EVENT_ALLOWLISTS = {
  inbound_order_created: {
    required: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "supplier_id", "inbound_order_id", "unit_price"],
    allowed: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "supplier_id", "inbound_order_id", "unit_price"],
  },
  outbound_order_created: {
    required: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "reason", "outbound_order_id"],
    allowed: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "reason", "outbound_order_id"],
  },
  stock_waste_registered: {
    required: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "reason", "outbound_order_id"],
    allowed: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "reason", "outbound_order_id"],
  },
  stock_threshold_triggered: {
    required: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "minimum_quantity", "threshold_version"],
    allowed: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "minimum_quantity", "threshold_version"],
  },
  direct_stock_edit_rejected: {
    required: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "rejection_code"],
    allowed: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "rejection_code"],
  },
  ingredient_price_variance_detected: {
    required: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "supplier_id", "current_unit_price", "historical_unit_price", "variance_percent", "threshold_percent", "inbound_order_id"],
    allowed: ["location_id", "country", "product_id", "product_category", "quantity", "unit", "currency", "supplier_id", "current_unit_price", "historical_unit_price", "variance_percent", "threshold_percent", "inbound_order_id"],
  },
  section_viewed: {
    required: ["section_id", "client_area", "navigation_source"],
    allowed: ["section_id", "client_area", "navigation_source"],
  },
  workflow_started: {
    required: ["workflow_id", "workflow_instance_id", "entry_source"],
    allowed: ["workflow_id", "workflow_instance_id", "entry_source"],
  },
  workflow_completed: {
    required: ["workflow_id", "workflow_instance_id", "elapsed_seconds"],
    allowed: ["workflow_id", "workflow_instance_id", "elapsed_seconds"],
  },
  workflow_abandoned: {
    required: ["workflow_id", "workflow_instance_id", "last_completed_step", "elapsed_seconds", "completion_state"],
    allowed: ["workflow_id", "workflow_instance_id", "last_completed_step", "elapsed_seconds", "completion_state"],
  },
  api_latency_recorded: {
    required: ["route_template", "http_method", "status_code", "duration_ms", "sample_rate", "service_name"],
    allowed: ["route_template", "http_method", "status_code", "duration_ms", "sample_rate", "service_name"],
  },
  api_request_failed: {
    required: ["route_template", "http_method", "status_code", "error_code", "retryable", "service_name"],
    allowed: ["route_template", "http_method", "status_code", "error_code", "retryable", "service_name"],
  },
  frontend_error_captured: {
    required: ["error_fingerprint", "component_area", "severity", "release", "occurrence_count_bucket"],
    allowed: ["error_fingerprint", "component_area", "severity", "release", "occurrence_count_bucket"],
  },
  incident_analysis_completed: {
    required: ["total_records", "valid_records", "invalid_records", "duration_ms", "file_size_bytes"],
    allowed: ["total_records", "valid_records", "invalid_records", "duration_ms", "file_size_bytes"],
  },
  incident_analysis_failed: {
    required: ["failure_stage", "error_code", "file_size_bytes", "duration_ms"],
    allowed: ["failure_stage", "error_code", "file_size_bytes", "duration_ms"],
  },
};

const queue = [];
let flushInProgress = false;

export function track(eventType, properties) {
  const allowlist = EVENT_ALLOWLISTS[eventType];
  if (!allowlist || !isAllowedProperties(properties, allowlist)) return;

  queue.push({
    eventId: createUuid(),
    timestamp: new Date().toISOString(),
    sessionId: SESSION_ID,
    userId: PSEUDONYMOUS_USER_ID,
    event_type: eventType,
    schemaVersion: SCHEMA_VERSION,
    requestId: globalThis.__BRASALAND_ACTIVE_REQUEST_ID__ || createUuid(),
    properties: Object.fromEntries(allowlist.allowed.map((key) => [key, properties[key]])),
  });

  if (queue.length >= MAX_BATCH_SIZE) void flushQueue();
  if (typeof document !== "undefined" && document.visibilityState === "hidden") void flushWithBeacon();
}

function isAllowedProperties(properties, allowlist) {
  if (!properties || typeof properties !== "object" || Array.isArray(properties)) return false;
  const keys = Object.keys(properties);
  return keys.every((key) => allowlist.allowed.includes(key))
    && allowlist.required.every((key) => Object.hasOwn(properties, key));
}

function createUuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    return (character === "x" ? random : (random & 0x3) | 0x8).toString(16);
  });
}

function getPseudonymousUserId() {
  const userId = globalThis.BRASALAND_PSEUDONYMOUS_USER_ID;
  return typeof userId === "string" && /^[A-Za-z0-9_-]{8,128}$/.test(userId) ? userId : null;
}

async function getEndpoint() {
  const config = await loadPublicConfig();
  return config.NEXT_PUBLIC_TELEMETRY_ENDPOINT;
}

async function flushQueue(keepalive = false) {
  if (flushInProgress || queue.length === 0) return;
  flushInProgress = true;
  const batch = queue.splice(0, queue.length);
  try {
    await sendBatch(batch, true);
  } finally {
    flushInProgress = false;
    if (queue.length >= MAX_BATCH_SIZE) void flushQueue();
  }
}

async function sendBatch(events, keepalive, attempt = 1) {
  try {
    const endpoint = await getEndpoint();
    if (!endpoint) throw new Error("Telemetry endpoint is not configured.");
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
      keepalive,
    });
    if (!response.ok) throw new Error(`Telemetry endpoint returned ${response.status}.`);
  } catch {
    if (attempt >= MAX_RETRIES) return;
    await new Promise((resolve) => setTimeout(resolve, RETRY_BASE_MS * (2 ** (attempt - 1))));
    await sendBatch(events, keepalive, attempt + 1);
  }
}

async function flushWithBeacon() {
  if (queue.length === 0) return;
  const batch = queue.splice(0, queue.length);
  try {
    const endpoint = await getEndpoint();
    const body = new Blob([JSON.stringify({ events: batch })], { type: "application/json" });
    if (!endpoint || !globalThis.navigator?.sendBeacon?.(endpoint, body)) {
      queue.unshift(...batch);
      void flushQueue(true);
    }
  } catch {
    queue.unshift(...batch);
    void flushQueue(true);
  }
}

if (typeof document !== "undefined") {
  const timer = setInterval(() => void flushQueue(), BATCH_INTERVAL_MS);
  timer.unref?.();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") void flushWithBeacon();
  });
}