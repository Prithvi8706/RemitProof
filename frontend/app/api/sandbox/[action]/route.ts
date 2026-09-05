const ACTIONS = new Set(["capabilities", "examples", "investigate"]);
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? process.env.API_URL ?? "http://127.0.0.1:8001";
export const maxDuration = 150;

async function proxy(request: Request, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  if (!ACTIONS.has(action)) return Response.json({ detail: "Unknown sandbox route" }, { status: 404 });
  if ((request.method === "POST") !== (action === "investigate")) {
    return Response.json({ detail: "Method not allowed" }, { status: 405 });
  }
  let body: Uint8Array | undefined;
  if (request.method === "POST") {
    if (request.headers.get("origin") && request.headers.get("origin") !== new URL(request.url).origin) {
      return Response.json({ detail: "Submit from this website" }, { status: 403 });
    }
    const reader = request.body?.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    if (reader) {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 65536) {
          await reader.cancel();
          return Response.json({ detail: "Scenario exceeds the 64 KiB limit" }, { status: 413 });
        }
        chunks.push(value);
      }
    }
    body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.length; }
  }
  try {
    const response = await fetch(`${API_URL}/api/sandbox/${action}`, {
      method: request.method, cache: "no-store", signal: AbortSignal.timeout(135000),
      headers: { "Content-Type": "application/json" },
      body: body ? Buffer.from(body) : undefined,
    });
    if (!response.headers.get("content-type")?.includes("application/json")) {
      return Response.json({ detail: "Investigation service is unavailable. Your scenario is still in the editor." }, { status: 502 });
    }
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ detail: "Investigation service timed out or is unavailable. Your scenario is still in the editor." }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
