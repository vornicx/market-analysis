import { createSupabaseServer } from "@/lib/supabase/server";
import { notFound } from "next/navigation";

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
      "*, events(home_team, away_team, commence_time), alert_evidence(payload), llm_analyses(*), telegram_deliveries(*), alert_feedback(*)"
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
        <b>{alert.alert_type}</b> · score <b>{alert.alert_score}</b> ·{" "}
        {alert.confidence_band.toUpperCase()} · {alert.market_key}
      </p>
      <p>{alert.reason_summary}</p>

      {alert.llm_analyses && alert.llm_analyses.status === "ok" && (
        <section style={{ border: "1px solid #2a2d34", borderRadius: 8, padding: 12, margin: "16px 0" }}>
          <b>🤖 LLM (advisory)</b>: {alert.llm_analyses.classification} —{" "}
          {alert.llm_analyses.summary}
        </section>
      )}

      <h2>Evidence</h2>
      <pre style={{ background: "#16181d", padding: 12, borderRadius: 8, overflow: "auto", fontSize: 12 }}>
        {JSON.stringify(alert.alert_evidence?.payload, null, 2)}
      </pre>

      <h2>Deliveries</h2>
      <ul>
        {(alert.telegram_deliveries ?? []).map((d: { id: string; chat_id: string; status: string }) => (
          <li key={d.id}>{d.chat_id} — {d.status}</li>
        ))}
      </ul>
    </div>
  );
}
