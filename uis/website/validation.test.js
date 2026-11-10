const assert = require("node:assert/strict");
const test = require("node:test");
const { citiesByCountry, locationsByCity, isValidEmail, hasFullName, isValidPhone, isAdult } = require("./validation.js");

test("country and city options cover both markets", () => {
  assert.deepEqual(citiesByCountry.CO, ["Medellín", "Bogotá", "Cali"]);
  assert.deepEqual(citiesByCountry.US, ["Miami", "Orlando"]);
});

test("favorite locations are scoped to the selected city", () => {
  assert.deepEqual(locationsByCity["CO|Medellín"], [
    "Brasaland El Poblado",
    "Brasaland Laureles",
    "Brasaland Envigado",
    "Brasaland Sabaneta",
  ]);
  assert.deepEqual(locationsByCity["CO|Bogotá"], ["Brasaland Usaquén", "Brasaland Chapinero", "Brasaland Zona Rosa"]);
  assert.deepEqual(locationsByCity["CO|Cali"], ["Brasaland Granada", "Brasaland Ciudad Jardín", "Brasaland Unicentro"]);
  assert.deepEqual(locationsByCity["US|Miami"], ["Brasaland Brickell", "Brasaland Coral Gables"]);
  assert.deepEqual(locationsByCity["US|Orlando"], ["Brasaland Downtown", "Brasaland International Drive"]);
  assert.equal(Object.values(locationsByCity).flat().length, 14);
});

test("email validation requires a valid domain", () => {
  assert.equal(isValidEmail("ana@example.com"), true);
  assert.equal(isValidEmail("ana+brasa@example.co"), true);
  assert.equal(isValidEmail("ana@local"), false);
  assert.equal(isValidEmail("ana@.com"), false);
  assert.equal(isValidEmail("ana@brasaland..com"), false);
});

test("full names contain at least two name parts", () => {
  assert.equal(hasFullName("Ana María Ospina"), true);
  assert.equal(hasFullName("Jean-Luc Durand"), true);
  assert.equal(hasFullName("Ana"), false);
  assert.equal(hasFullName("Ana -"), false);
});

test("phone validation requires the selected country's code and ten digits", () => {
  assert.equal(isValidPhone("+57 300 123 4567", "CO"), true);
  assert.equal(isValidPhone("+1 305 123 4567", "US"), true);
  assert.equal(isValidPhone("+57 300-123-4567", "CO"), true);
  assert.equal(isValidPhone("+57 abc3001234567", "CO"), false);
  assert.equal(isValidPhone("+1 305 123 4567", "CO"), false);
  assert.equal(isValidPhone("300 123 4567", "CO"), false);
});

test("eligibility excludes people who are exactly 18 or younger", () => {
  const today = new Date("2026-11-10T00:00:00");
  assert.equal(isAdult("2007-11-09", today), true);
  assert.equal(isAdult("2008-11-10", today), false);
  assert.equal(isAdult("2010-11-10", today), false);
  assert.equal(isAdult("2027-01-01", today), false);
  assert.equal(isAdult("", today), false);
});
