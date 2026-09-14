"use client";

import { useRef, useState } from "react";
import { BriefArticle } from "@/components/BriefArticle";
import { CompanyHeader } from "@/components/CompanyHeader";
import { DesignTimeline } from "@/components/DesignTimeline";
import { EmailEngine } from "@/components/EmailEngine";
import { FinancialCharts } from "@/components/FinancialCharts";
import { NewsRail } from "@/components/NewsRail";
import { SearchBar } from "@/components/SearchBar";
import { SignalCards } from "@/components/SignalCards";
import { Skeleton } from "@/components/Skeleton";
import { isThin } from "@/lib/normalize";
import type { Research } from "@/lib/types";

export default function Page() {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<Research | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // Only the newest request is allowed to write state; an impatient second
  // search must not be overwritten by the first one landing late.
  const runId = useRef(0);

  const run = async (refresh: boolean) => {
    const company = query.trim();
    if (!company || loading) return;
    const id = ++runId.current;
    setLoading(true);
    setError("");
    if (refresh) setData(null);

    try {
      const res = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company, refresh }),
      });
      const json = await res.json();
      if (id !== runId.current) return;
      if (!res.ok) throw new Error(json?.error ?? `Request failed (${res.status}).`);
      setData(json as Research);
    } catch (e) {
      if (id !== runId.current) return;
      setData(null);
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      if (id === runId.current) setLoading(false);
    }
  };

  return (
    <main className="shell">
      <header className="masthead">
        <div className="wordmark">Account Intelligence</div>
        <p className="tagline">
          One company name in. Verified signals, the products they point to, and outreach a rep can
          send today.
        </p>
        <SearchBar
          value={query}
          onChange={setQuery}
          onSubmit={() => run(false)}
          onRefresh={() => run(true)}
          loading={loading}
          canRefresh={Boolean(data)}
        />
      </header>

      {error && (
        <section>
          <div className="notice error">{error}</div>
        </section>
      )}

      {loading && <Skeleton />}

      {!loading && !data && !error && (
        <section>
          <div className="card empty">
            Every claim on the page carries a date and a source. Where the research finds nothing,
            the section stays empty rather than filling with plausible numbers.
          </div>
        </section>
      )}

      {!loading && data && (
        <>
          <CompanyHeader
            company={data.company}
            generatedAt={data.generatedAt}
            cached={data.cached}
          />
          {(data.limitations || isThin(data)) && (
            <section>
              <div className="notice">
                {data.limitations ||
                  "Limited public information available for this company — the sections below show only what could be verified."}
              </div>
            </section>
          )}
          <SignalCards signals={data.signals} />
          <EmailEngine emails={data.emails} signals={data.signals} />
          <DesignTimeline milestones={data.designTimeline} />
          <NewsRail news={data.news} />
          <FinancialCharts
            quarters={data.financials.quarters}
            rdSpend={data.financials.rdSpend}
          />
          <BriefArticle article={data.article} />
        </>
      )}
    </main>
  );
}
