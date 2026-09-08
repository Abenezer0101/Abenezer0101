import type { Quarter, RDYear } from "@/lib/types";

// One fixed coordinate space, scaled by the browser. No chart library, no
// resize observers, no hydration mismatch.
const W = 460;
const H = 190;
const PAD = { l: 36, r: 10, t: 20, b: 28 };
const PLOT_W = W - PAD.l - PAD.r;
const PLOT_H = H - PAD.t - PAD.b;
const BASE = PAD.t + PLOT_H;

// One decimal rule per axis, so 0.00 / 6.20 / 12.4 cannot appear on one scale.
const axisFmt = (max: number) => {
  const dp = max >= 100 ? 0 : max >= 10 ? 1 : 2;
  return (v: number) => v.toFixed(dp);
};
/** Round the axis up to a readable step, which also buys the tallest value
 *  label clearance from the top gridline. */
const STEPS = [1, 1.2, 1.4, 1.6, 1.8, 2, 2.5, 3, 4, 5, 6, 8];
const niceMax = (v: number) => {
  const raw = v * 1.05;
  const mag = 10 ** Math.floor(Math.log10(raw));
  for (const s of STEPS) if (raw <= s * mag) return s * mag;
  return 10 * mag;
};

function Grid({ max }: { max: number }) {
  const lines = [0, 0.5, 1];
  const fmt = axisFmt(max);
  return (
    <g>
      {lines.map((f) => {
        const y = BASE - PLOT_H * f;
        return (
          <g key={f}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y} y2={y} stroke="#e3e1d9" strokeWidth={1} />
            <text className="axis" x={PAD.l - 6} y={y + 3} textAnchor="end">
              {fmt(max * f)}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function RevenueChart({ quarters }: { quarters: Quarter[] }) {
  const max = niceMax(Math.max(...quarters.map((q) => q.revenue), 0.0001));
  const fmt = axisFmt(max);
  const slot = PLOT_W / quarters.length;
  const bw = slot * 0.5;
  const sw = slot * 0.24;

  return (
    <div className="card chart">
      <div className="chart-head">
        <h3>Quarterly revenue</h3>
        <div className="legend">
          <span>
            <i style={{ background: "#cfe0de" }} />
            Total
          </span>
          <span>
            <i style={{ background: "#0b6e6e" }} />
            Lead segment
          </span>
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Quarterly revenue in billions">
        <Grid max={max} />
        {quarters.map((q, i) => {
          const cx = PAD.l + slot * (i + 0.5);
          const h = (PLOT_H * q.revenue) / max;
          const sh = (PLOT_H * Math.min(q.segmentRevenue, q.revenue)) / max;
          return (
            <g key={`${q.label}-${i}`}>
              <rect x={cx - bw / 2} y={BASE - h} width={bw} height={h} fill="#cfe0de" rx={2} />
              <rect x={cx - sw / 2} y={BASE - sh} width={sw} height={sh} fill="#0b6e6e" rx={2} />
              <text className="val" x={cx} y={BASE - h - 6} textAnchor="middle">
                {fmt(q.revenue)}
              </text>
              <text className="axis" x={cx} y={BASE + 15} textAnchor="middle">
                {q.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function RDChart({ rdSpend }: { rdSpend: RDYear[] }) {
  const max = niceMax(Math.max(...rdSpend.map((r) => r.amount), 0.0001));
  const fmt = axisFmt(max);
  const slot = PLOT_W / rdSpend.length;
  const pt = (r: RDYear, i: number) => ({
    x: PAD.l + slot * (i + 0.5),
    y: BASE - (PLOT_H * r.amount) / max,
  });

  return (
    <div className="card chart">
      <div className="chart-head">
        <h3>R&amp;D spend</h3>
        <div className="legend">
          <span>Billions, with share of revenue</span>
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Annual research and development spend">
        <Grid max={max} />
        <polyline
          fill="none"
          stroke="#0b6e6e"
          strokeWidth={1.75}
          points={rdSpend.map((r, i) => { const p = pt(r, i); return `${p.x},${p.y}`; }).join(" ")}
        />
        {rdSpend.map((r, i) => {
          const p = pt(r, i);
          return (
            <g key={`${r.year}-${i}`}>
              <circle cx={p.x} cy={p.y} r={3.5} fill="#0b6e6e" />
              <text className="val" x={p.x} y={p.y - 8} textAnchor="middle">
                {fmt(r.amount)}
              </text>
              <text className="axis" x={p.x} y={BASE + 15} textAnchor="middle">
                {r.year}
              </text>
              {r.pctOfRevenue > 0 && (
                <text className="axis" x={p.x} y={BASE + 26} textAnchor="middle">
                  {r.pctOfRevenue.toFixed(1)}%
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function FinancialCharts({
  quarters,
  rdSpend,
}: {
  quarters: Quarter[];
  rdSpend: RDYear[];
}) {
  if (quarters.length === 0 && rdSpend.length === 0) return null;
  return (
    <section>
      <h2 className="section-label">Money</h2>
      <div className="charts">
        {quarters.length > 0 && <RevenueChart quarters={quarters} />}
        {rdSpend.length > 0 && <RDChart rdSpend={rdSpend} />}
      </div>
    </section>
  );
}
