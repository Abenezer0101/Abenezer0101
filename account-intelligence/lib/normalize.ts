import {
  MILESTONE_TYPES,
  PERSONAS,
  PRODUCTS,
  type EmailVariant,
  type Milestone,
  type NewsItem,
  type Quarter,
  type RDYear,
  type Research,
  type Signal,
} from "./types";

const s = (v: unknown): string => (typeof v === "string" ? v.trim() : "");

/** "$11.5B" / "11.5 billion" / 11.5 -> 11.5. Anything unparseable -> null, so a
 *  bad row is dropped instead of rendering a zero-height bar that reads as fact. */
const n = (v: unknown): number | null => {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (typeof v !== "string") return null;
  const m = v.replace(/,/g, "").match(/-?\d+(\.\d+)?/);
  return m ? Number(m[0]) : null;
};

const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const oneOf = <T extends readonly string[]>(v: unknown, set: T): T[number] | null =>
  typeof v === "string" && (set as readonly string[]).includes(v) ? (v as T[number]) : null;

const YYYY_MM = /^\d{4}-(0[1-9]|1[0-2])$/;

/** The model is right most of the time. This turns "most of the time" into
 *  "always renderable": coerce what is coercible, drop what is not, never throw. */
export function normalize(raw: unknown, fallbackName: string): Research {
  const r = (raw ?? {}) as Record<string, any>;
  const c = (r.company ?? {}) as Record<string, unknown>;
  const fin = (r.financials ?? {}) as Record<string, unknown>;

  const news: NewsItem[] = list(r.news)
    .map((x: any) => ({
      headline: s(x?.headline),
      date: s(x?.date),
      summary: s(x?.summary),
      source: s(x?.source),
    }))
    .filter((x) => x.headline);

  const quarters: Quarter[] = list(fin.quarters)
    .map((x: any) => {
      const revenue = n(x?.revenue);
      return revenue === null
        ? null
        : { label: s(x?.label), revenue, segmentRevenue: n(x?.segmentRevenue) ?? revenue };
    })
    .filter((x): x is Quarter => x !== null && x.label !== "");

  const rdSpend: RDYear[] = list(fin.rdSpend)
    .map((x: any) => {
      const amount = n(x?.amount);
      return amount === null
        ? null
        : { year: s(x?.year), amount, pctOfRevenue: n(x?.pctOfRevenue) ?? 0 };
    })
    .filter((x): x is RDYear => x !== null && x.year !== "");

  // A milestone without a real YYYY-MM cannot be placed on the axis. Guessing a
  // month would put a fabricated date in front of a rep on a call.
  const designTimeline: Milestone[] = list(r.designTimeline)
    .map((x: any) => {
      const type = oneOf(x?.type, MILESTONE_TYPES);
      const date = s(x?.date);
      return type && YYYY_MM.test(date) && s(x?.label)
        ? { date, label: s(x.label), type }
        : null;
    })
    .filter((x): x is Milestone => x !== null);

  const signals: Signal[] = list(r.signals)
    .map((x: any) => {
      const product = oneOf(x?.product, PRODUCTS);
      return product && s(x?.signal)
        ? {
            signal: s(x.signal),
            date: s(x?.date),
            source: s(x?.source),
            meaning: s(x?.meaning),
            product,
            evidenceLine: s(x?.evidenceLine),
          }
        : null;
    })
    .filter((x): x is Signal => x !== null);

  const seen = new Set<string>();
  const emails: EmailVariant[] = list(r.emails)
    .map((x: any) => {
      const persona = oneOf(x?.persona, PERSONAS);
      if (!persona || seen.has(persona) || !s(x?.body)) return null;
      seen.add(persona);
      return { persona, angle: s(x?.angle), subject: s(x?.subject), body: s(x.body) };
    })
    .filter((x): x is EmailVariant => x !== null)
    .sort((a, b) => PERSONAS.indexOf(a.persona) - PERSONAS.indexOf(b.persona));

  return {
    company: {
      name: s(c.name) || fallbackName,
      ticker: s(c.ticker),
      hq: s(c.hq),
      ceo: s(c.ceo),
      employees: s(c.employees),
      segments: list(c.segments).map(s).filter(Boolean),
    },
    news,
    financials: { quarters, rdSpend },
    designTimeline,
    signals,
    article: s(r.article),
    emails,
    limitations: s(r.limitations) || undefined,
    generatedAt: new Date().toISOString(),
  };
}

/** True when the model found so little that the page should say so up front. */
export const isThin = (r: Research) =>
  r.signals.length === 0 && r.news.length === 0 && r.financials.quarters.length === 0;
