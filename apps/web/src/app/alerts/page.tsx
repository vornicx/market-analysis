import Link from "next/link";
import { createSupabaseServer } from "@/lib/supabase/server";
import { RealtimeAlerts } from "@/components/RealtimeAlerts";

export const dynamic = "force-dynamic";

export default async function AlertsPage({
  searchParams,
}: {
  searchParams: Promise<{ segment?: string; band?: string }>;
}) {
  const { segment, band } = await searchParams;
  const supabase = await createSupabaseServer();

  let query = supabase
    .from("alerts")
    .select("*, events(home_team, away_team)")
    .order("created_at", { ascending: false })
    .limit(50);
  if (segment) query = query.eq("segment_key", segment);
  if (band) query = query.eq("confidence_band", band);
  const { data: alerts } = await query;

  return (
    <div>
      <h1>Alerts</h1>
      <RealtimeAlerts />
      <div style={{ marginBottom: 12, display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Link href="/alerts">All</Link>
        <Link href="/alerts?segment=general_football">⚽ General</Link>
        <Link href="/alerts?segment=world_cup">🏆 World Cup</Link>
        <span className="muted">|</span>
        <Link href="/alerts?band=high">High only</Link>
        <Link href="/alerts?band=medium">Medium only</Link>
      </div>
      {!alerts?.length ? (
        <p className="muted">No alerts match — lower filters or check worker status.</p>
      ) : (
        <table className="data">
          <thead>
            <tr>
              <th>Time</th><th>Seg</th><th>Match</th><th>Market</th>
              <th>Type</th><th>Score</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id}>
                <td className="muted">{new Date(a.created_at).toLocaleString()}</td>
                <td>{a.segment_key === "world_cup" ? "🏆" : "⚽"}</td>
                <td>
                  <Link href={`/alerts/${a.id}`}>
                    {a.events?.home_team} vs {a.events?.away_team}
                  </Link>
                </td>
                <td>{a.market_key}</td>
                <td>{a.alert_type}</td>
                <td>
                  <span className={`pill ${a.confidence_band}`}>{a.alert_score}</span>
                </td>
                <td className="muted">{a.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
