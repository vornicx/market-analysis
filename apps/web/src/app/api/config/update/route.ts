import { z } from "zod";
import { apiError, apiOk } from "@/lib/api";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

const bodySchema = z.object({
  key: z.string().min(1),
  value: z.union([z.string(), z.number(), z.boolean()]),
});

const ALLOWED_KEYS = [
  "daily_credit_cap",
  "monthly_credit_cap",
  "worker_poll_floor_seconds",
  "alert_suppression_minutes",
  "odds_api_region",
  "llm_enabled",
  "football_enabled",
  "world_cup_enabled",
  "world_cup_only_mode",
  "global_pause",
  "dry_run",
];

export async function POST(req: Request) {
  const parsed = bodySchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return apiError("VALIDATION", "Body must be { key, value }", 422);
  const { key, value } = parsed.data;
  if (!ALLOWED_KEYS.includes(key)) return apiError("VALIDATION", `Unknown key: ${key}`, 422);

  const db = createSupabaseAdmin();
  const { data: before } = await db.from("monitor_configs").select("*").eq("id", 1).single();
  const { data: after, error: dbErr } = await db
    .from("monitor_configs")
    .update({ [key]: value, updated_at: new Date().toISOString() })
    .eq("id", 1)
    .select()
    .single();
  if (dbErr) return apiError("INTERNAL", dbErr.message, 500);

  await db.from("audit_logs").insert({
    actor_id: null,
    action: `config.update.${key}`,
    entity: "monitor_configs",
    entity_id: "1",
    before: { [key]: before?.[key] },
    after: { [key]: value },
  });

  return apiOk({ config: after });
}
