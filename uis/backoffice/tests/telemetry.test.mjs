import assert from "node:assert/strict";
import test from "node:test";

test("track batches allowlisted events and builds the standard envelope", async () => {
  const requests = [];
  globalThis.document = { visibilityState: "visible", addEventListener() {} };
  globalThis.window = { addEventListener() {} };
  globalThis.fetch = async (url, options) => {
    if (String(url).endsWith(".env.local")) {
      return { ok: true, text: async () => "NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:8000/telemetry/events" };
    }
    requests.push({ url: String(url), body: JSON.parse(options.body) });
    return { ok: true, status: 200 };
  };

  const { track } = await import("../src/services/telemetry.mjs?test");
  const validProperties = {
    section_id: "operations",
    client_area: "backoffice",
    navigation_source: "unknown",
  };

  track("section_viewed", { ...validProperties, email: "not-allowed@example.com" });
  for (let index = 0; index < 20; index += 1) track("section_viewed", validProperties);
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, "http://localhost:8000/telemetry/events");
  assert.equal(requests[0].body.events.length, 20);
  for (const event of requests[0].body.events) {
    assert.match(event.eventId, /^[0-9a-f-]{36}$/);
    assert.match(event.timestamp, /^\d{4}-\d\d-\d\dT/);
    assert.match(event.sessionId, /^[0-9a-f-]{36}$/);
    assert.equal(event.userId, null);
    assert.equal(event.event_type, "section_viewed");
    assert.equal(event.schemaVersion, "1.0.0");
    assert.match(event.requestId, /^[0-9a-f-]{36}$/);
    assert.deepEqual(Object.keys(event.properties).sort(), ["client_area", "navigation_source", "section_id"]);
  }
});

test("track retries the same batch with its original event ids", async () => {
  let attempts = 0;
  const batches = [];
  globalThis.document = { visibilityState: "visible", addEventListener() {} };
  globalThis.window = { addEventListener() {} };
  globalThis.fetch = async (url, options) => {
    if (String(url).endsWith(".env.local")) {
      return { ok: true, text: async () => "NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:8000/telemetry/events" };
    }
    attempts += 1;
    batches.push(JSON.parse(options.body));
    return { ok: attempts === 3, status: attempts === 3 ? 200 : 503 };
  };

  const { track } = await import("../src/services/telemetry.mjs?retry-test");
  for (let index = 0; index < 20; index += 1) {
    track("section_viewed", {
      section_id: "operations",
      client_area: "backoffice",
      navigation_source: "unknown",
    });
  }
  await new Promise((resolve) => setTimeout(resolve, 1_600));

  assert.equal(attempts, 3);
  assert.deepEqual(
    batches.map((batch) => batch.events.map((event) => event.eventId)),
    [0, 1, 2].map(() => batches[0].events.map((event) => event.eventId)),
  );
});

test("track flushes a pending batch through sendBeacon when the page is hidden", async () => {
  let visibilityListener;
  const beacons = [];
  globalThis.document = {
    visibilityState: "visible",
    addEventListener(name, listener) {
      if (name === "visibilitychange") visibilityListener = listener;
    },
  };
  globalThis.window = { addEventListener() {} };
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { sendBeacon: (url, body) => { beacons.push({ url, body }); return true; } },
  });
  globalThis.fetch = async (url) => {
    if (String(url).endsWith(".env.local")) {
      return { ok: true, text: async () => "NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:8000/telemetry/events" };
    }
    throw new Error("Pending event should use sendBeacon.");
  };

  const { track } = await import("../src/services/telemetry.mjs?beacon-test");
  track("section_viewed", {
    section_id: "operations",
    client_area: "backoffice",
    navigation_source: "unknown",
  });
  document.visibilityState = "hidden";
  visibilityListener();
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(beacons.length, 1);
  assert.equal(beacons[0].url, "http://localhost:8000/telemetry/events");
  assert.match(beacons[0].body.type, /^application\/json/);
});