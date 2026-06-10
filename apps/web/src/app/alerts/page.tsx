import Link from "next/link";
import { createSupabaseServer } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

const BAND_COLORS: Record<string, string> = {
  high: "#ff7b7b",
  medium: "#ffc66d",
  low: "#9ecbff",
};

export default async function AlertsPage({
  searchParams,
}: {
  searchParams: Promise<{ segment?: string }>;
}) {
  const { segment } = await searchParams;
  const supabase = await createSupabaseServer();

  let query = supabase
    .from("alerts")
    .select("*, events(home_team, away_team)")
    .order("created_at", { ascending: false })
    .limit(50);
  if (segment) query = query.eq("segment_key", segment);
  const { data: alerts } = await query;

  return (
    <div>
      <h1>Alerts</h1>
      <div style={{ marginBottom: 12 }}>
        <Link href="/alerts" style={{ marginRight: 8, color: "#9ecbff" }}>All</Link>
        <Link href="/alerts?segment=general_football" style={{ marginRight: 8, color: "#9ecbff" }}>⚽ General</Link>
        <Link href="/alerts?segment=world_cup" style={{ color: "#9ecbff" }}>🏆 World Cup</Link>
      </div>
      {!alerts?.length ? (
        <p style={{ color: "#888" }}>
          No alerts yet. Check worker status if you expected activity.
        </p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "#888" }}>
              <th>Time</th><th>Segment</th><th>Match</th><th>Market</th>
              <th>Type</th><th>Score</th><th>Band</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id} style={{ borderTop: "1px solid #2a2d34" }}>
                <td>{new Date(a.created_at).toLocaleString()}</td>
                <td>{a.segment_key === "world_cup" ? "🏆 WC" : "⚽ GEN"}</td>
                <td>
                  <Link href={`/alerts/${a.id}`} style={{ color: "#9ecbff" }}>
                    {a.events?.home_team} vs {a.events?.away_team}
                  </Link>
                </td>
                <td>{a.market_key}</td>
                <td>{a.alert_type}</td>
                <td style={{ fontWeight: 700 }}>{a.alert_score}</td>
                <td style={{ color: BAND_COLORS[a.confidence_band] }}>{a.confidence_band}</td>
                <td>{a.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
