import Link from "next/link";
import { createSupabaseAdmin } from "@/lib/supabase/admin";
import { RealtimeAlerts } from "@/components/RealtimeAlerts";

export const dynamic = "force-dynamic";

export default async function AlertsPage({
  searchParams,
}: {
  searchParams: Promise<{ segment?: string; band?: string }>;
}) {
  const { segment, band } = await searchParams;
  const supabase = createSupabaseAdmin();

  let query = supabase
    .from("alerts")
    .select("*, events(home_team, away_team)")
    .order("created_at", { ascending: false })
    .limit(50);
  if (segment) query = query.eq("segment_key", segment);
  if (band) query = query.eq("confidence_band", band);
  const { data: alerts } = await query;

  const filters = [
    { href: "/alerts", label: "All", active: !segment && !band },
    { href: "/alerts?segment=general_football", label: "\u26BD General", active: segment === "general_football" },
    { href: "/alerts?segment=world_cup", label: "\uD83C\uDFC6 World Cup", active: segment === "world_cup" },
    { href: "/alerts?band=high", label: "High", active: band === "high" },
    { href: "/alerts?band=medium", label: "Medium", active: band === "medium" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1>Alerts</h1>
        <RealtimeAlerts />
      </div>

      <div className="filters">
        {filters.map((f) => (
          <Link key={f.href} href={f.href} className={`filter-btn${f.active ? " active" : ""}`}>
            {f.label}
          </Link>
        ))}
      </div>

      {!alerts?.length ? (
        <div className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <p className="muted">No alerts match — lower filters or check worker status.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th><th>Seg</th><th>Match</th><th>Market</th>
                <th>Type</th><th>Score</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id}>
                  <td className="muted text-sm">{new Date(a.created_at).toLocaleString()}</td>
                  <td>{a.segment_key === "world_cup" ? "\uD83C\uDFC6" : "\u26BD"}</td>
                  <td>
                    <Link href={`/alerts/${a.id}`}>
                      {a.events?.home_team} vs {a.events?.away_team}
                    </Link>
                  </td>
                  <td className="muted">{a.market_key}</td>
                  <td><span className="pill" style={{ background: "var(--surface-elevated)" }}>{a.alert_type}</span></td>
                  <td><span className={`pill ${a.confidence_band}`}>{a.alert_score}</span></td>
                  <td><span className={`pill ${a.status}`}>{a.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
