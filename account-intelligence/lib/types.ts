export const PRODUCTS = [
  "Calibre",
  "Tessent",
  "Veloce",
  "Questa",
  "Solido",
  "Catapult",
] as const;
export type Product = (typeof PRODUCTS)[number];

export const MILESTONE_TYPES = ["tapeout", "launch", "node", "packaging"] as const;
export type MilestoneType = (typeof MILESTONE_TYPES)[number];

export const PERSONAS = ["Executive", "Engineering Leader", "Technical Evaluator"] as const;
export type Persona = (typeof PERSONAS)[number];

export type Signal = {
  signal: string; // "Active TSMC N2 production across CPU and GPU programs"
  date: string; // "May 2026" - human readable, not ISO
  source: string; // "AMD Q2 2026 earnings call"
  meaning: string; // one sentence: what it means for their engineers
  product: Product;
  evidenceLine: string; // the sentence a rep can say out loud
};

export type Milestone = {
  date: string; // "2026-07"  YYYY-MM for sorting
  label: string; // "MI400 series launch"
  type: MilestoneType;
};

export type EmailVariant = {
  persona: Persona;
  angle: string; // "Roadmap risk across overlapping design starts"
  subject: string;
  body: string;
};

export type NewsItem = { headline: string; date: string; summary: string; source: string };
export type Quarter = { label: string; revenue: number; segmentRevenue: number };
export type RDYear = { year: string; amount: number; pctOfRevenue: number };

export type Research = {
  company: {
    name: string;
    ticker: string;
    hq: string;
    ceo: string;
    employees: string;
    segments: string[];
  };
  news: NewsItem[];
  financials: {
    quarters: Quarter[];
    rdSpend: RDYear[];
  };
  designTimeline: Milestone[];
  signals: Signal[];
  article: string; // 2-3 paragraphs, \n\n separated
  emails: EmailVariant[];
  generatedAt: string;
  /** Set when public information was too thin to fill a section honestly. */
  limitations?: string;
  cached?: boolean;
};
