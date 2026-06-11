import Link from "next/link";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const supabase = createSupabaseAdmin();
  const since24h = new Date(Date.now() - 24 * 3600_000).toISOString();
  const midnight = new Date();
  midnight.setUTCHours(0, 0, 0, 0);

  const [{ data: config }, { data: runs }, { count: alerts24h }, { data: latest }] =
    await Promise.all([
      supabase.from("monitor_configs").select("*").eq("id", 1).single(),
      supabase
        .from("worker_runs")
        .select("started_at, credits_used, status")
        .gte("started_at", midnight.toISOString())
        .order("started_at", { ascending: false }),
      supabase
        .from("alerts")
        .select("id", { count: "exact", head: true })
        .gte("created_at", since24h),
      supabase
        .from("alerts")
        .select("id, created_at, segment_key, alert_type, alert_score, confidence_band, events(home_team, away_team)")
        .order("created_at", { ascending: false })
        .limit(10),
    ]);

  const lastRun = runs?.[0];
  const creditsToday = (runs ?? []).reduce((sum, r) => sum + (r.credits_used ?? 0), 0);
  const heartbeatMin = lastRun
    ? Math.round((Date.now() - new Date(lastRun.started_at).getTime()) / 60000)
    : null;

  const mode = !config
    ? "UNKNOWN"
    : config.global_pause
      ? "PAUSED"
      : config.world_cup_only_mode
        ? "WORLD CUP"
        : "NORMAL";

  const capPct = config ? Math.min((creditsToday / config.daily_credit_cap) * 100, 100) : 0;
  const capTone = config && creditsToday >= config.daily_credit_cap ? "danger" : capPct > 75 ? "warn" : "ok";

  return (
    <div>
      <h1>Overview</h1>

      {config?.dry_run && (
        <div className="banner warn">⚠ DRY RUN — alerts are computed and stored but NOT sent to Telegram.</div>
      )}
      {config?.global_pause && (
        <div className="banner danger">⏸ GLOBAL PAUSE — worker is idling.</div>
      )}

      <div className="stat-grid">
        <div className="card">
          <div className="card-label">Mode</div>
          <div className="card-value">{mode}</div>
          <div className="card-sub">{config?.world_cup_only_mode ? "World Cup only" : "Standard monitoring"}</div>
        </div>

        <div className="card">
          <div className="card-label">Alerts (24h)</div>
          <div className="card-value">{alerts24h ?? 0}</div>
          <div className="card-sub">
            {latest && latest.length > 0 ? `${latest.length} most recent shown` : "No alerts yet"}
          </div>
        </div>

        <div className="card">
          <div className="card-label">Worker Heartbeat</div>
          <div className="card-value" style={{ color: heartbeatMin === null || heartbeatMin > 30 ? "var(--danger)" : "var(--ok)" }}>
            <span className={`dot ${heartbeatMin === null || heartbeatMin > 30 ? "danger" : "ok"}`} />
            {heartbeatMin === null ? "Offline" : `${heartbeatMin}m ago`}
          </div>
          <div className="card-sub">{lastRun ? `Status: ${lastRun.status}` : "No runs yet"}</div>
        </div>

        <div className="card">
          <div className="card-label">Daily Credits</div>
          <div className="card-value">{creditsToday}<span style={{ fontSize: 14, fontWeight: 400, color: "var(--text-secondary)" }}> / {config?.daily_credit_cap ?? "?"}</span></div>
          <div className="card-sub" style={{ marginTop: 8 }}>
            <div className="progress">
              <div className={`progress-bar ${capTone}`} style={{ width: `${capPct}%` }} />
            </div>
          </div>
        </div>
      </div>

      <h2>Latest alerts</h2>
      {!latest?.length ? (
        <div className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <p className="muted">No alerts yet. The worker will generate alerts as it processes odds data.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th><th>Seg</th><th>Match</th><th>Type</th><th>Score</th>
              </tr>
            </thead>
            <tbody>
              {latest.map((a) => (
                <tr key={a.id}>
                  <td className="muted text-sm">{new Date(a.created_at).toLocaleString()}</td>
                  <td>{a.segment_key === "world_cup" ? "🏆" : "⚽"}</td>
                  <td>
                    <Link href={`/alerts/${a.id}`}>
                      {(a.events as { home_team?: string })?.home_team} vs{" "}
                      {(a.events as { away_team?: string })?.away_team}
                    </Link>
                  </td>
                  <td><span className="pill" style={{ background: "var(--surface-elevated)" }}>{a.alert_type}</span></td>
                  <td><span className={`pill ${a.confidence_band}`}>{a.alert_score}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
