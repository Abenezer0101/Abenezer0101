import type { Milestone, MilestoneType } from "@/lib/types";

const COLORS: Record<MilestoneType, string> = {
  tapeout: "#B45309", // amber — the buying moment, so the loudest
  launch: "#0B6E6E",
  node: "#5B21B6",
  packaging: "#166534",
};

const LABELS: Record<MilestoneType, string> = {
  tapeout: "Tapeout",
  launch: "Launch",
  node: "Node transition",
  packaging: "Packaging",
};

/** YYYY-MM to an absolute month index. Returns NaN for anything malformed so a
 *  single bad date drops one marker instead of collapsing the whole axis. */
const toMonths = (d: string): number => {
  const m = /^(\d{4})-(\d{2})$/.exec(d.trim());
  if (!m) return NaN;
  const year = Number(m[1]);
  const month = Number(m[2]);
  if (month < 1 || month > 12) return NaN;
  return year * 12 + month;
};

const MONTH_NAMES = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ");
const pretty = (d: string) => {
  const [y, m] = d.split("-");
  return `${MONTH_NAMES[Number(m) - 1]} ${y}`;
};

export function DesignTimeline({ milestones }: { milestones: Milestone[] }) {
  const valid = milestones
    .map((m) => ({ ...m, t: toMonths(m.date) }))
    .filter((m) => Number.isFinite(m.t))
    .sort((a, b) => a.t - b.t);

  if (valid.length === 0) return null;

  const min = valid[0].t;
  const max = valid[valid.length - 1].t;
  const span = max - min;
  const pct = (t: number) => (span === 0 ? 50 : ((t - min) / span) * 100);

  const now = new Date();
  const nowPct = pct(now.getFullYear() * 12 + now.getMonth() + 1);
  const types = Array.from(new Set(valid.map((m) => m.type)));

  return (
    <section>
      <h2 className="section-label">Design and silicon calendar</h2>
      <div className="card">
        <div className="tl-scroll">
        <div className="timeline">
          <div className="tl-axis" />
          {nowPct >= 0 && nowPct <= 100 && (
            <div className="tl-now" style={{ left: `${nowPct}%` }}>
              <span>Today</span>
            </div>
          )}
          {valid.map((m, i) => {
            const x = pct(m.t);
            const up = i % 2 === 0;
            // Edge markers would hang off the card if every label were centred.
            const shift = x < 12 ? "0%" : x > 88 ? "-100%" : "-50%";
            const align = x < 12 ? "left" : x > 88 ? "right" : "center";
            return (
              <div key={`${m.date}-${m.label}-${i}`}>
                <div
                  className="tl-dot"
                  style={{ left: `${x}%`, background: COLORS[m.type] }}
                  title={`${pretty(m.date)} — ${m.label}`}
                />
                <div className={`tl-stem ${up ? "up" : "down"}`} style={{ left: `${x}%` }} />
                <div
                  className={`tl-item ${up ? "up" : "down"}`}
                  style={{ left: `${x}%`, transform: `translateX(${shift})`, textAlign: align }}
                >
                  <div className="tl-date" style={{ color: COLORS[m.type] }}>
                    {pretty(m.date)}
                  </div>
                  <div className="tl-label">{m.label}</div>
                </div>
              </div>
            );
          })}
        </div>
        </div>
        <div className="tl-legend">
          {types.map((t) => (
            <span key={t}>
              <i style={{ background: COLORS[t] }} />
              {LABELS[t]}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
