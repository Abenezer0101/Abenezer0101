import type { Signal } from "@/lib/types";

export function SignalCards({ signals }: { signals: Signal[] }) {
  if (signals.length === 0) return null;
  return (
    <section>
      <h2 className="section-label">Signals, and what to sell against them</h2>
      <div className="signals">
        {signals.map((s, i) => (
          <article className="card signal" key={`${s.product}-${i}`}>
            <div className="signal-head">
              <span className="product">{s.product}</span>
              <span className="meta">{s.date}</span>
            </div>
            <h3>{s.signal}</h3>
            {s.meaning && <p className="means">{s.meaning}</p>}
            {s.evidenceLine && (
              <div className="evidence">
                <b>Say this</b>
                {s.evidenceLine}
              </div>
            )}
            {s.source && <footer>Source: {s.source}</footer>}
          </article>
        ))}
      </div>
    </section>
  );
}
