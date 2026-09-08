import type { Research } from "@/lib/types";

const Fact = ({ label, value }: { label: string; value: string }) =>
  value ? (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  ) : null;

export function CompanyHeader({
  company,
  generatedAt,
  cached,
}: {
  company: Research["company"];
  generatedAt: string;
  cached?: boolean;
}) {
  const when = new Date(generatedAt);
  return (
    <section>
      <div className="card">
        <div className="company-top">
          <h1>{company.name}</h1>
          {company.ticker && <span className="ticker">{company.ticker}</span>}
        </div>
        <dl className="facts">
          <Fact label="Headquarters" value={company.hq} />
          <Fact label="Chief executive" value={company.ceo} />
          <Fact label="Employees" value={company.employees} />
        </dl>
        {company.segments.length > 0 && (
          <div className="segments">
            {company.segments.map((s) => (
              <span className="chip" key={s}>
                {s}
              </span>
            ))}
          </div>
        )}
        <p className="meta" style={{ marginTop: 18, marginBottom: 0 }}>
          {cached ? "Served from cache" : "Researched"}{" "}
          {Number.isNaN(when.getTime()) ? "just now" : when.toLocaleString()}
        </p>
      </div>
    </section>
  );
}
