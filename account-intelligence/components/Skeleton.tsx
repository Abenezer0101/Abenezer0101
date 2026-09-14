"use client";

import { useEffect, useState } from "react";

const STAGES = [
  "Searching recent news",
  "Gathering financials",
  "Mapping design activity",
  "Matching signals to products",
  "Drafting outreach",
];

const Bar = ({ w, h = 13 }: { w: string; h?: number }) => (
  <div className="sk" style={{ width: w, height: h, marginTop: 10 }} />
);

const Block = ({ children }: { children?: React.ReactNode }) => (
  <section>
    <div className="sk" style={{ width: 132, height: 11, marginBottom: 12 }} />
    <div className="card">{children}</div>
  </section>
);

export function Skeleton() {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    // Honest pacing: the last stage holds rather than looping back to the first,
    // which would suggest the run restarted.
    const id = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 8000);
    return () => clearInterval(id);
  }, []);

  return (
    <div aria-busy="true" aria-live="polite">
      <section>
        <div className="card">
          <Bar w="42%" h={24} />
          <Bar w="70%" />
          <Bar w="55%" />
        </div>
      </section>
      <section>
        <div className="status" style={{ marginTop: 20 }}>
          <i />
          {STAGES[stage]}…
        </div>
      </section>
      <Block>
        <Bar w="88%" />
        <Bar w="64%" />
      </Block>
      <Block>
        <div className="sk" style={{ width: "100%", height: 150 }} />
      </Block>
      <Block>
        <div className="sk" style={{ width: "100%", height: 190 }} />
      </Block>
      <Block>
        <Bar w="92%" />
        <Bar w="78%" />
        <Bar w="84%" />
      </Block>
      <Block>
        <Bar w="90%" />
        <Bar w="86%" />
        <Bar w="60%" />
      </Block>
      <Block>
        <Bar w="40%" />
        <Bar w="94%" />
        <Bar w="72%" />
      </Block>
    </div>
  );
}
