import { test } from "node:test";
import assert from "node:assert/strict";
import { blankScenario, parseScenario, errorMessage } from "./sandbox.ts";

test("scenario exports round-trip with exact decimal strings", () => {
  const scenario = blankScenario();
  scenario.payment.amount = "9007199254740993.01";
  assert.deepEqual(parseScenario(JSON.stringify(scenario)), scenario);
});
test("malformed imports cannot crash record or proposal editors", () => {
  for (const patch of [{ invoices: [null] }, { customers: {} }, { payment: [] }, { proposal: {} }, { schema_version: 2 }]) {
    assert.throws(() => parseScenario(JSON.stringify({ ...blankScenario(), ...patch })));
  }
});
test("live mode cannot smuggle a supplied hypothesis", () => {
  assert.throws(() => parseScenario(JSON.stringify({ ...blankScenario(), mode: "live_ai" })));
  assert.equal(parseScenario(JSON.stringify({ ...blankScenario(), mode: "live_ai", proposal: null })).mode, "live_ai");
});
test("validation errors identify the field needing correction", () => {
  assert.equal(errorMessage({ detail: [{ path: "payment.amount", message: "Invalid amount" }] }), "payment.amount: Invalid amount");
});
