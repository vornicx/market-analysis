import { z } from "zod";
import { requireAdmin } from "@/lib/auth";
import { apiError, apiOk } from "@/lib/api";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

export async function GET() {
  const { user, error } = await requireAdmin();
  if (error) return error;

  const db = createSupabaseAdmin();
  const [{ data: config }, { data: segments }] = await Promise.all([
    db.from("monitor_configs").select("*").eq("id", 1).single(),
    db.from("monitor_segments").select("*").order("segment_key"),
  ]);
  return apiOk({ config, segments });
}

const patchSchema = z
  .object({
    football_enabled: z.boolean(),
    world_cup_enabled: z.boolean(),
    world_cup_only_mode: z.boolean(),
    global_pause: z.boolean(),
    dry_run: z.boolean(),
    llm_enabled: z.boolean(),
    daily_credit_cap: z.number().int().min(1).max(10000),
    monthly_credit_cap: z.number().int().min(1).max(300000),
    odds_api_region: z.enum(["eu", "uk", "us", "au"]),
    worker_poll_floor_seconds: z.number().int().min(60).max(3600),
    alert_suppression_minutes: z.number().int().min(5).max(1440),
  })
  .partial()
  .strict();

export async function PATCH(req: Request) {
  const { user, error } = await requireAdmin();
  if (error) return error;

  const parsed = patchSchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) {
    return apiError("VALIDATION", parsed.error.issues.map((i) => i.message).join("; "), 422);
  }

  const db = createSupabaseAdmin();
  const { data: before } = await db.from("monitor_configs").select("*").eq("id", 1).single();
  const { data: after, error: dbErr } = await db
    .from("monitor_configs")
    .update({ ...parsed.data, updated_by: user!.id, updated_at: new Date().toISOString() })
    .eq("id", 1)
    .select()
    .single();
  if (dbErr) return apiError("INTERNAL", dbErr.message, 500);

  await db.from("audit_logs").insert({
    actor_id: user!.id,
    action: "config.update",
    entity: "monitor_configs",
    entity_id: "1",
    before,
    after,
  });
  return apiOk({ config: after });
}
