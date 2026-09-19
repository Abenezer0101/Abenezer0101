"use client";

import { useMemo, useState } from "react";
import type { EmailVariant, Signal } from "@/lib/types";

const mailto = (e: EmailVariant) =>
  `mailto:?subject=${encodeURIComponent(e.subject)}&body=${encodeURIComponent(e.body)}`;

const STOP = new Set(
  "the a an and or of to in on for with by at from is are was were their its this that as it we you our your".split(
    " ",
  ),
);
const words = (s: string) =>
  new Set(
    s
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length > 3 && !STOP.has(w)),
  );

/** The model never links an email to a signal explicitly, so infer it: the
 *  signal sharing the most distinctive words with the draft is the one the rep
 *  is leaning on. Product name is worth more than any other single token. */
function matchSignal(email: EmailVariant, signals: Signal[]): Signal | null {
  if (signals.length === 0) return null;
  const text = `${email.angle} ${email.subject} ${email.body}`;
  const haystack = words(text);
  const lower = text.toLowerCase();
  let best: Signal | null = null;
  let bestScore = 0;
  for (const s of signals) {
    let score = lower.includes(s.product.toLowerCase()) ? 3 : 0;
    for (const w of words(`${s.signal} ${s.meaning}`)) if (haystack.has(w)) score += 1;
    if (score > bestScore) {
      bestScore = score;
      best = s;
    }
  }
  return bestScore >= 2 ? best : null;
}

export function EmailEngine({ emails, signals }: { emails: EmailVariant[]; signals: Signal[] }) {
  const [active, setActive] = useState(0);
  const [copied, setCopied] = useState(false);
  const email = emails[active];
  const linked = useMemo(() => (email ? matchSignal(email, signals) : null), [email, signals]);

  if (emails.length === 0) return null;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${email.subject}\n\n${email.body}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section>
      <h2 className="section-label">Outreach</h2>
      <div className="card">
        <div className="tabs" role="tablist">
          {emails.map((e, i) => (
            <button
              key={e.persona}
              role="tab"
              aria-selected={i === active}
              onClick={() => {
                setActive(i);
                setCopied(false);
              }}
            >
              {e.persona}
            </button>
          ))}
        </div>
        {email.angle && <p className="angle">{email.angle}</p>}
        {linked && (
          <div className="segments" style={{ marginTop: 10 }}>
            <span className="chip">
              Built on: {linked.signal} ({linked.date})
            </span>
          </div>
        )}
        <div className="subject">
          <b>Subject</b>
          {email.subject}
        </div>
        <p className="body">{email.body}</p>
        <div className="actions">
          <button onClick={copy}>Copy</button>
          <a href={mailto(email)}>Open in mail</a>
          {copied && <span className="copied">Copied</span>}
        </div>
      </div>
    </section>
  );
}
