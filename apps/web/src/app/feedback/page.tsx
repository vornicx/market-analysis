import { createSupabaseServer } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function FeedbackPage() {
  const supabase = await createSupabaseServer();
  const { data: rows } = await supabase
    .from("alert_feedback")
    .select("*, alerts(alert_type, alert_score, confidence_band, segment_key)")
    .order("created_at", { ascending: false })
    .limit(100);

  return (
    <div>
      <h1>Feedback review</h1>
      {!rows?.length ? (
        <p style={{ color: "#888" }}>No feedback yet — review alerts and mark them useful/noise.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "#888" }}>
              <th>Time</th><th>Segment</th><th>Type</th><th>Score</th><th>Band</th><th>Verdict</th><th>Note</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => (
              <tr key={f.id} style={{ borderTop: "1px solid #2a2d34" }}>
                <td>{new Date(f.created_at).toLocaleString()}</td>
                <td>{f.alerts?.segment_key}</td>
                <td>{f.alerts?.alert_type}</td>
                <td>{f.alerts?.alert_score}</td>
                <td>{f.alerts?.confidence_band}</td>
                <td><b>{f.verdict}</b></td>
                <td>{f.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
