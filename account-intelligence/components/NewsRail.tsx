import type { NewsItem } from "@/lib/types";

export function NewsRail({ news }: { news: NewsItem[] }) {
  if (news.length === 0) return null;
  return (
    <section>
      <h2 className="section-label">Recent developments</h2>
      <div className="rail">
        {news.map((n, i) => (
          <article className="card" key={`${n.headline}-${i}`}>
            <div className="meta">{n.date}</div>
            <h3>{n.headline}</h3>
            <p>{n.summary}</p>
            <footer>{n.source}</footer>
          </article>
        ))}
      </div>
    </section>
  );
}
