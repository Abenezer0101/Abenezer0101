import { MILESTONE_TYPES, PERSONAS, PRODUCTS } from "./types";

const str = { type: "string" as const };
const num = { type: "number" as const };

/** Every object needs additionalProperties:false and a full `required` list, or
 *  the API rejects the tool as non-strict. Numeric/length constraints are not
 *  supported in strict schemas - counts are enforced in the prompt instead. */
const obj = <T extends Record<string, unknown>>(properties: T) => ({
  type: "object" as const,
  properties,
  required: Object.keys(properties),
  additionalProperties: false as const,
});

const arr = (items: unknown) => ({ type: "array" as const, items });

export const RESEARCH_SCHEMA = obj({
  company: obj({
    name: str,
    ticker: str,
    hq: str,
    ceo: str,
    employees: str,
    segments: arr(str),
  }),
  news: arr(obj({ headline: str, date: str, summary: str, source: str })),
  financials: obj({
    quarters: arr(obj({ label: str, revenue: num, segmentRevenue: num })),
    rdSpend: arr(obj({ year: str, amount: num, pctOfRevenue: num })),
  }),
  designTimeline: arr(
    obj({ date: str, label: str, type: { type: "string", enum: [...MILESTONE_TYPES] } }),
  ),
  signals: arr(
    obj({
      signal: str,
      date: str,
      source: str,
      meaning: str,
      product: { type: "string", enum: [...PRODUCTS] },
      evidenceLine: str,
    }),
  ),
  article: str,
  emails: arr(
    obj({
      persona: { type: "string", enum: [...PERSONAS] },
      angle: str,
      subject: str,
      body: str,
    }),
  ),
  limitations: str,
});

export const EMIT_TOOL = {
  name: "emit_research",
  description:
    "Emit the finished account intelligence package. Call exactly once, after all web research is complete.",
  strict: true,
  input_schema: RESEARCH_SCHEMA,
} as const;
