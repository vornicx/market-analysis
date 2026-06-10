import { createSupabaseServer } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { AlertActions } from "@/components/AlertActions";
import { EvidenceView } from "@/components/EvidenceView";

export const dynamic = "force-dynamic";

export default async function AlertDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createSupabaseServer();

  const { data: alert } = await supabase
    .from("alerts")
    .select(
      "*, events(home_team, away_team, commence_time), alert_evidence(payload), llm_analyses(*), telegram_deliveries(*), alert_feedback(verdict, note, created_at)"
    )
    .eq("id", id)
    .maybeSingle();

  if (!alert) notFound();

  return (
    <div>
      <h1>
        {alert.segment_key === "world_cup" ? "🏆" : "⚽"}{" "}
        {alert.events?.home_team} vs {alert.events?.away_team}
      </h1>
      <p>
        <span className={`pill ${alert.confidence_band}`}>
          {alert.alert_score}/100 · {alert.confidence_band.toUpperCase()}
        </span>{" "}
        <b>{alert.alert_type}</b> · {alert.market_key} · status: {alert.status}
      </p>
      <p>{alert.reason_summary}</p>

      <AlertActions alertId={alert.id} status={alert.status} />

      {alert.llm_analyses?.status === "ok" && (
        <div className="banner info">
          🤖 <b>LLM (advisory)</b>: {alert.llm_analyses.classification?.replace(/_/g, " ")} —{" "}
          {alert.llm_analyses.summary}
        </div>
      )}

      {alert.alert_evidence?.payload ? (
        <EvidenceView payload={alert.alert_evidence.payload} />
      ) : (
        <p className="muted">No evidence payload stored.</p>
      )}

      <h2>Deliveries</h2>
      {(alert.telegram_deliveries ?? []).length === 0 ? (
        <p className="muted">No deliveries.</p>
      ) : (
        <table className="data">
          <thead>
            <tr><th>Chat</th><th>Status</th><th>Error</th></tr>
          </thead>
          <tbody>
            {alert.telegram_deliveries.map(
              (d: { id: string; chat_id: string; status: string; error: string | null }) => (
                <tr key={d.id}>
                  <td><code>{d.chat_id}</code></td>
                  <td>{d.status}</td>
                  <td className="muted">{d.error}</td>
                </tr>
              )
            )}
          </tbody>
        </table>
      )}

      {(alert.alert_feedback ?? []).length > 0 && (
        <>
          <h2>Feedback</h2>
          <ul>
            {alert.alert_feedback.map(
              (f: { verdict: string; note: string | null; created_at: string }, i: number) => (
                <li key={i}>
                  <b>{f.verdict}</b> {f.note && `— ${f.note}`}{" "}
                  <span className="muted">({new Date(f.created_at).toLocaleString()})</span>
                </li>
              )
            )}
          </ul>
        </>
      )}
    </div>
  );
}
