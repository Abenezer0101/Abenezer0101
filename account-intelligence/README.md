# Account Intelligence

A rep types a company name. One API route runs a research pass with web search,
returns a schema-validated package, caches it, and the page renders seven
sections: company header, signals mapped to Siemens EDA products, a three-persona
email generator, a silicon calendar, a news rail, financial charts, and a brief.

No database, no auth, no multi-page routing. One page, one route, one data shape.

## Two versions

**`app/` + `lib/` — the Next.js app.** Live web search through the Claude API, so every
fact is researched at request time. Needs your own API key and a server.

**`standalone.html` — one file, no build, no key.**
[Published here](https://claude.ai/code/artifact/9975c053-b2f4-4380-a172-2ee2f33bee5e).
Same seven sections, but it asks Claude from the page on the viewer's own account,
and that runtime **cannot browse** — the briefing comes from model recall, not
research. It says so at the top and puts a Verify link on every sourced claim.
Open it to see the thing working; use the Next.js app when the facts have to hold up.

## Run it

```bash
cp .env.local.example .env.local   # add your ANTHROPIC_API_KEY
npm install
npm run dev
```

Open http://localhost:3000 and search for a company. The first run takes 60-120
seconds — that is web search plus a full research pass, not a hung request.
Results are cached per company in memory; **Refresh** forces a new run.

| Env var | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Server-side only; it never reaches the browser. |
| `ANTHROPIC_MODEL` | `claude-opus-5` | Any model that supports web search and strict tool use. |
| `ANTHROPIC_EFFORT` | `medium` | `low` … `max`. Higher costs more and takes longer. |

## Shape of the thing

```
app/page.tsx              the only stateful component
app/api/research/route.ts the model call, the cache, the error surface
components/               props in, markup out
lib/types.ts              the JSON contract everything else conforms to
lib/prompt.ts             system prompt + Siemens product mapping
lib/schema.ts             the strict tool schema the model must fill
lib/normalize.ts          coerce what is coercible, drop what is not
lib/cache.ts              an in-memory Map
```

Swapping the data source later means replacing one `fetch` in `page.tsx` and one
route file. Nothing in `components/` knows where the data came from.

## Three decisions worth knowing about

**The model fills a tool, not a text box.** Instructing a model to return only
JSON works most of the time, not all of the time. Instead it calls a strict tool
(`lib/schema.ts`) whose schema the API enforces, so `product` cannot come back as
a hallucinated product name and the payload arrives pre-parsed. Text parsing
survives as a fallback for the rare turn where the model narrates instead.

**Bad data is dropped, never guessed.** `lib/normalize.ts` coerces `"$11.5B"` to
`11.5`, drops a milestone whose date is not `YYYY-MM` rather than inventing a
month for it, and filters products and personas to the known unions. A section
with nothing verifiable renders as nothing, and thin coverage — a private
company, no filings — surfaces as a notice at the top of the page.

**Web search turns pause.** A server-tool turn stops with
`stop_reason: "pause_turn"` roughly every ten search iterations; the route
resumes it up to four times. Without that, long research silently returns half an
answer. `maxDuration = 120` matters for the same reason: the platform's default
serverless timeout kills a search run mid-flight and it surfaces as a generic
fetch failure.

## Charts

Hand-rolled SVG in a fixed `viewBox`, scaled by the browser. No chart library, no
resize observers, no hydration mismatch, no dependency to keep current. The
timeline is absolute positioning over a percentage axis, with edge labels clamped
so they do not hang off the card, and horizontal scroll below 760px rather than a
pile of overlapping text.
