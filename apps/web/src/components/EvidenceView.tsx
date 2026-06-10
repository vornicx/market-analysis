/** Renders alert evidence as a readable breakdown instead of raw JSON. */

interface DetectorEntry {
  fired: boolean;
  points: number;
  evidence: Record<string, unknown>;
}

interface SeriesPoint {
  polled_at: string;
  implied_prob: number;
}

export function EvidenceView({ payload }: { payload: Record<string, unknown> }) {
  const detectors = (payload?.detectors ?? {}) as Record<string, DetectorEntry>;
  const consensus = (payload?.consensus_series ?? []) as SeriesPoint[];
  const bookSeries = (payload?.book_series ?? {}) as Record<string, SeriesPoint[]>;

  return (
    <div>
      <h2>Detector breakdown</h2>
      <table className="data">
        <thead>
          <tr><th>Detector</th><th>Fired</th><th>Points</th><th>Evidence</th></tr>
        </thead>
        <tbody>
          {Object.entries(detectors)
            .sort(([, a], [, b]) => Math.abs(b.points) - Math.abs(a.points))
            .map(([name, d]) => (
              <tr key={name} style={{ opacity: d.fired ? 1 : 0.45 }}>
                <td><code>{name}</code></td>
                <td>{d.fired ? "✓" : "—"}</td>
                <td style={{ fontWeight: 600, color: d.points < 0 ? "var(--danger)" : undefined }}>
                  {d.points > 0 ? `+${d.points}` : d.points}
                </td>
                <td><code style={{ fontSize: 11 }}>{JSON.stringify(d.evidence)}</code></td>
              </tr>
            ))}
        </tbody>
      </table>

      {consensus.length > 1 && (
        <>
          <h2>Consensus implied probability</h2>
          <PriceSparkline series={consensus} />
        </>
      )}

      {Object.keys(bookSeries).length > 0 && (
        <>
          <h2>Per-book price path</h2>
          <table className="data">
            <thead>
              <tr>
                <th>Book</th>
                {(Object.values(bookSeries)[0] ?? []).slice(-6).map((p) => (
                  <th key={p.polled_at}>
                    {new Date(p.polled_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(bookSeries).map(([book, series]) => (
                <tr key={book}>
                  <td><code>{book}</code></td>
                  {series.slice(-6).map((p) => (
                    <td key={p.polled_at}>{Number(p.implied_prob).toFixed(3)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function PriceSparkline({ series }: { series: SeriesPoint[] }) {
  const values = series.map((p) => Number(p.implied_prob));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 400;
  const h = 60;
  const points = values
    .map((v, i) => `${(i / (values.length - 1)) * w},${h - ((v - min) / range) * (h - 8) - 4}`)
    .join(" ");

  return (
    <div>
      <svg width={w} height={h} style={{ background: "var(--surface)", borderRadius: 8 }}>
        <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth={2} />
      </svg>
      <div className="muted" style={{ fontSize: 12 }}>
        {values[0].toFixed(3)} → {values[values.length - 1].toFixed(3)} (Δp{" "}
        {((values[values.length - 1] - values[0]) * 100).toFixed(1)} pts)
      </div>
    </div>
  );
}
