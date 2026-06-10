import { createSupabaseServer } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function StatusPage() {
  const supabase = await createSupabaseServer();
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

  return (
    <div>
      <h1>System status</h1>
      <p>
        Worker heartbeat:{" "}
        {last ? (
          <b style={{ color: ageMin! > 30 ? "#ff7b7b" : "#7bdc8a" }}>
            {ageMin} min ago ({last.status})
          </b>
        ) : (
          <b style={{ color: "#ff7b7b" }}>never seen</b>
        )}
        {" · "}Credits used today: <b>{todayCredits}</b>
      </p>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ textAlign: "left", color: "#888" }}>
            <th>Started</th><th>Type</th><th>Segments</th><th>Credits</th>
            <th>Snapshots</th><th>Alerts</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {(runs ?? []).map((r) => (
            <tr key={r.id} style={{ borderTop: "1px solid #2a2d34" }}>
              <td>{new Date(r.started_at).toLocaleString()}</td>
              <td>{r.cycle_type}</td>
              <td>{(r.segments ?? []).join(", ")}</td>
              <td>{r.credits_used}</td>
              <td>{r.snapshots_written}</td>
              <td>{r.alerts_created}</td>
              <td style={{ color: r.status === "error" ? "#ff7b7b" : undefined }}>{r.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
