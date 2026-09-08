import Anthropic from "@anthropic-ai/sdk";
import { cache } from "@/lib/cache";
import { normalize } from "@/lib/normalize";
import { SYSTEM, buildPrompt } from "@/lib/prompt";
import { EMIT_TOOL } from "@/lib/schema";

export const runtime = "nodejs";
// Web search plus a full research pass runs well past the platform's default
// serverless timeout. Without this the request dies as an opaque "failed to fetch".
export const maxDuration = 120;

const MODEL = process.env.ANTHROPIC_MODEL ?? "claude-opus-5";
const EFFORT = (process.env.ANTHROPIC_EFFORT ??
  "medium") as Anthropic.Messages.OutputConfig["effort"];
// A server-tool turn pauses every 10 search iterations; resuming is the caller's job.
const MAX_RESUMES = 4;

export async function POST(req: Request) {
  let company = "";
  let refresh = false;
  try {
    const body = await req.json();
    company = typeof body?.company === "string" ? body.company.trim() : "";
    refresh = body?.refresh === true;
  } catch {
    return Response.json({ error: "Malformed request body." }, { status: 400 });
  }
  if (!company) return Response.json({ error: "Company name is required." }, { status: 400 });

  const key = company.toLowerCase();
  const hit = cache.get(key);
  if (!refresh && hit) return Response.json({ ...hit, cached: true });

  if (!process.env.ANTHROPIC_API_KEY) {
    return Response.json(
      { error: "ANTHROPIC_API_KEY is not set on the server." },
      { status: 500 },
    );
  }

  const client = new Anthropic();
  const messages: Anthropic.MessageParam[] = [{ role: "user", content: buildPrompt(company) }];

  try {
    let message: Anthropic.Message | null = null;

    for (let i = 0; i <= MAX_RESUMES; i++) {
      const stream = client.messages.stream({
        model: MODEL,
        max_tokens: 16000,
        system: SYSTEM,
        // Adaptive thinking is on by default on Opus 5; effort is the cost dial.
        output_config: { effort: EFFORT },
        tools: [
          { type: "web_search_20260209", name: "web_search", max_uses: 12 },
          EMIT_TOOL,
        ],
        messages,
      });
      message = await stream.finalMessage();

      if (message.stop_reason !== "pause_turn") break;
      // Resume: hand the paused assistant turn straight back, no extra user text.
      messages.push({ role: "assistant", content: message.content });
    }

    if (!message) return Response.json({ error: "No response from the model." }, { status: 502 });
    if (message.stop_reason === "refusal") {
      return Response.json({ error: "The model declined this request." }, { status: 502 });
    }

    const payload = extractPayload(message);
    if (!payload) {
      const reason =
        message.stop_reason === "max_tokens"
          ? "The research ran past the token limit before it could be assembled."
          : "The model returned no usable research package.";
      return Response.json({ error: reason }, { status: 502 });
    }

    const result = normalize(payload, company);
    cache.set(key, result);
    return Response.json(result);
  } catch (err) {
    return Response.json({ error: describe(err) }, { status: statusOf(err) });
  }
}

/** The strict tool gives us pre-parsed, schema-valid JSON. The text fallback
 *  exists for the rare turn where the model narrates the package instead of
 *  calling the tool - slicing the outermost braces survives a stray preamble. */
function extractPayload(message: Anthropic.Message): unknown {
  for (const block of message.content) {
    if (block.type === "tool_use" && block.name === EMIT_TOOL.name) return block.input;
  }
  const text = message.content
    .filter((b): b is Anthropic.TextBlock => b.type === "text")
    .map((b) => b.text)
    .join("\n");
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start === -1 || end <= start) return null;
  try {
    return JSON.parse(text.slice(start, end + 1));
  } catch {
    return null;
  }
}

function statusOf(err: unknown): number {
  return err instanceof Anthropic.APIError && typeof err.status === "number" ? err.status : 500;
}

function describe(err: unknown): string {
  if (err instanceof Anthropic.RateLimitError) return "Rate limited by the API. Try again shortly.";
  if (err instanceof Anthropic.AuthenticationError) return "The API key was rejected.";
  if (err instanceof Anthropic.APIConnectionTimeoutError) {
    return "The research call timed out. Retry, or try a narrower company name.";
  }
  if (err instanceof Anthropic.APIError) return err.message;
  return err instanceof Error ? err.message : "Unexpected server error.";
}
