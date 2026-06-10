import { requireAdmin } from "@/lib/auth";
import { apiError, apiOk } from "@/lib/api";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

/**
 * Queues a replay: the worker re-runs detectors over STORED snapshots for this
 * alert's selection with current thresholds (0 Odds API credits) and persists
 * the result as a status='replayed' alert. Processed within one worker cycle.
 */
export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { user, error } = await requireAdmin();
  if (error) return error;
  const { id } = await ctx.params;

  const db = createSupabaseAdmin();
  const { data: alert } = await db.from("alerts").select("id").eq("id", id).maybeSingle();
  if (!alert) return apiError("NOT_FOUND", "Alert not found", 404);

  const { data: existing } = await db
    .from("replay_requests")
    .select("id")
    .eq("alert_id", id)
    .eq("status", "pending")
    .maybeSingle();
  if (existing) return apiError("CONFLICT", "Replay already queued for this alert", 409);

  const { data: request, error: dbErr } = await db
    .from("replay_requests")
    .insert({ alert_id: id, requested_by: user!.id })
    .select()
    .single();
  if (dbErr) return apiError("INTERNAL", dbErr.message, 500);

  await db.from("audit_logs").insert({
    actor_id: user!.id,
    action: "alert.replay_requested",
    entity: "alerts",
    entity_id: id,
  });
  return apiOk({ replay: request }, 201);
}
