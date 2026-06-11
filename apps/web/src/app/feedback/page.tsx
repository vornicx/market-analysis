import { createSupabaseAdmin } from "@/lib/supabase/admin";

export const dynamic = "force-dynamic";

export default async function FeedbackPage() {
  const supabase = createSupabaseAdmin();
  const { data: rows } = await supabase
    .from("alert_feedback")
    .select("*, alerts(alert_type, alert_score, confidence_band, segment_key)")
    .order("created_at", { ascending: false })
    .limit(100);

  return (
    <div>
      <h1>Feedback Review</h1>
      {!rows?.length ? (
        <div className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <p className="muted">No feedback yet — review alerts and mark them useful/noise.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th><th>Segment</th><th>Type</th><th>Score</th><th>Band</th><th>Verdict</th><th>Note</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((f) => (
                <tr key={f.id}>
                  <td className="muted text-sm">{new Date(f.created_at).toLocaleString()}</td>
                  <td>{f.alerts?.segment_key}</td>
                  <td><span className="pill" style={{ background: "var(--surface-elevated)" }}>{f.alerts?.alert_type}</span></td>
                  <td>{f.alerts?.alert_score}</td>
                  <td><span className={`pill ${f.alerts?.confidence_band}`}>{f.alerts?.confidence_band}</span></td>
                  <td><b style={{ color: f.verdict === "useful" ? "var(--ok)" : f.verdict === "noise" ? "var(--danger)" : undefined }}>{f.verdict}</b></td>
                  <td className="muted">{f.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
