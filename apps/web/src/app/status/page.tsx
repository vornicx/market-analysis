import { createSupabaseAdmin } from "@/lib/supabase/admin";

export const dynamic = "force-dynamic";

export default async function StatusPage() {
  const supabase = createSupabaseAdmin();
  const { data: runs } = await supabase
    .from("worker_runs")
    .select("*")
    .order("started_at", { ascending: false })
    .limit(50);

  const last = runs?.[0];
  const ageMin = last ? Math.round((Date.now() - new Date(last.started_at).getTime()) / 60000) : null;
  const todayCredits = (runs ?? [])
    .filter((r) => new Date(r.started_at).toDateString() === new Date().toDateString())
    .reduce((sum, r) => sum + (r.credits_used ?? 0), 0);

  const okRuns = (runs ?? []).filter((r) => r.status === "ok").length;
  const errorRuns = (runs ?? []).filter((r) => r.status === "error").length;
  const successRate = runs?.length ? Math.round((okRuns / runs.length) * 100) : 0;

  return (
    <div>
      <h1>System Status</h1>

      <div className="stat-grid">
        <div className="card">
          <div className="card-label">Worker Status</div>
          <div className="card-value" style={{ color: ageMin === null || ageMin > 30 ? "var(--danger)" : "var(--ok)" }}>
            <span className={`dot ${ageMin === null || ageMin > 30 ? "danger" : "ok"}`} />
            {ageMin === null ? "Offline" : "Running"}
          </div>
          <div className="card-sub">{last ? `Last run ${ageMin} min ago` : "No runs recorded"}</div>
        </div>

        <div className="card">
          <div className="card-label">Success Rate</div>
          <div className="card-value">{successRate}%</div>
          <div className="card-sub">{okRuns} ok / {(okRuns + errorRuns)} total</div>
        </div>

        <div className="card">
          <div className="card-label">Credits Today</div>
          <div className="card-value">{todayCredits}</div>
          <div className="card-sub">Consumed this billing period</div>
        </div>

        <div className="card">
          <div className="card-label">Last Run Status</div>
          <div className="card-value" style={{ color: last?.status === "error" ? "var(--danger)" : "var(--ok)" }}>
            {last?.status ?? "N/A"}
          </div>
          <div className="card-sub">{last ? `${last.snapshots_written} snapshots, ${last.alerts_created} alerts` : ""}</div>
        </div>
      </div>

      <h2>Run History</h2>
      {!runs?.length ? (
        <div className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <p className="muted">No runs recorded yet.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Started</th><th>Type</th><th>Segments</th><th>Credits</th>
                <th>Snapshots</th><th>Alerts</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(runs ?? []).map((r) => (
                <tr key={r.id}>
                  <td className="muted text-sm">{new Date(r.started_at).toLocaleString()}</td>
                  <td><span className="pill" style={{ background: "var(--surface-elevated)" }}>{r.cycle_type}</span></td>
                  <td className="muted">{(r.segments ?? []).join(", ")}</td>
                  <td>{r.credits_used}</td>
                  <td>{r.snapshots_written}</td>
                  <td>{r.alerts_created}</td>
                  <td>
                    <span className={`pill ${r.status === "error" ? "danger" : "ok"}`}>
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
