import assert from "node:assert/strict";
import test from "node:test";
import { getConsistentBenchmarkPublication } from "./api.ts";

test("retries when benchmark endpoints briefly expose different generations", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  const generations = ["generation-a", "generation-b", "generation-b", "generation-b"];
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ evaluation_generation_id: generations.shift() }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });

  const publication = await getConsistentBenchmarkPublication(2);
  assert.equal(publication.benchmark.evaluation_generation_id, "generation-b");
  assert.equal(publication.caseData.evaluation_generation_id, "generation-b");
});

test("rejects a persistently mixed benchmark publication", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  let requestCount = 0;
  globalThis.fetch = async () => {
    requestCount += 1;
    const generation = requestCount % 2 === 1 ? "generation-a" : "generation-b";
    return new Response(JSON.stringify({ evaluation_generation_id: generation }), { status: 200 });
  };

  await assert.rejects(
    getConsistentBenchmarkPublication(2),
    /Benchmark publication changed while it was being loaded/,
  );
});
