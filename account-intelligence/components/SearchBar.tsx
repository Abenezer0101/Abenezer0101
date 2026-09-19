"use client";

const EXAMPLES = ["AMD", "Nvidia", "Tenstorrent", "Infineon"];

export function SearchBar({
  value,
  onChange,
  onSubmit,
  onRefresh,
  loading,
  canRefresh,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onRefresh: () => void;
  loading: boolean;
  canRefresh: boolean;
}) {
  return (
    <>
      <form
        className="search"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Company name — AMD, Tenstorrent, Bosch…"
          aria-label="Company name"
          autoFocus
        />
        <button type="submit" className="primary" disabled={loading || !value.trim()}>
          {loading ? "Researching…" : "Research"}
        </button>
        {canRefresh && (
          <button type="button" onClick={onRefresh} disabled={loading}>
            Refresh
          </button>
        )}
      </form>
      <div className="suggests">
        <span>Try</span>
        {EXAMPLES.map((c) => (
          <button key={c} type="button" disabled={loading} onClick={() => onChange(c)}>
            {c}
          </button>
        ))}
      </div>
    </>
  );
}
