export function BriefArticle({ article }: { article: string }) {
  const paragraphs = article.split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
  if (paragraphs.length === 0) return null;
  return (
    <section>
      <h2 className="section-label">The brief</h2>
      <div className="card article">
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    </section>
  );
}
