import { z } from "zod";
import { SEGMENT_KEYS } from "@market-monitor/shared";
import { apiError, apiOk } from "@/lib/api";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

const bodySchema = z.object({
  min_alert_score: z.number().min(0).max(100).optional(),
  enabled: z.boolean().optional(),
  polling_profile: z
    .object({
      gt48h: z.number().min(0).optional(),
      h48_24: z.number().min(0).optional(),
      h24_6: z.number().min(0).optional(),
      h6_1: z.number().min(0).optional(),
      lt1h: z.number().min(0).optional(),
    })
    .optional(),
  thresholds: z
    .object({
      price_move: z.object({ abs_dp_min: z.number().min(0), z_min: z.number().min(0) }).optional(),
      divergence: z.object({ divergence_min: z.number().min(0) }).optional(),
      drift: z.object({ drift_polls_min: z.number().min(0), drift_cum_min: z.number().min(0) }).optional(),
      sharp_leader: z.object({ sharp_dp_min: z.number().min(0), follower_count_min: z.number().min(0) }).optional(),
      persistence: z.object({ persistence_ratio_min: z.number().min(0).max(1) }).optional(),
      reversal: z.object({ reversal_ratio: z.number().min(0).max(1), reversal_window_polls: z.number().min(0) }).optional(),
      rarity: z.object({ rarity_pctile_min: z.number().min(0).max(100), rarity_min_samples: z.number().min(0) }).optional(),
    })
    .optional(),
});

export async function POST(req: Request, ctx: { params: Promise<{ key: string }> }) {
  const { key } = await ctx.params;
  if (!SEGMENT_KEYS.includes(key as any)) return apiError("NOT_FOUND", `Unknown segment: ${key}`, 404);

  const parsed = bodySchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return apiError("VALIDATION", "Invalid body", 422);

  const db = createSupabaseAdmin();
  const { data: before } = await db.from("monitor_segments").select("*").eq("segment_key", key).single();
  if (!before) return apiError("NOT_FOUND", "Segment not found", 404);

  const update: Record<string, any> = {};
  if (parsed.data.min_alert_score !== undefined) update.min_alert_score = parsed.data.min_alert_score;
  if (parsed.data.enabled !== undefined) update.enabled = parsed.data.enabled;
  if (parsed.data.polling_profile) {
    update.polling_profile = { ...before.polling_profile, ...parsed.data.polling_profile };
  }
  if (parsed.data.thresholds) {
    update.thresholds = { ...before.thresholds, ...parsed.data.thresholds };
  }

  const { data: after, error: dbErr } = await db
    .from("monitor_segments")
    .update({ ...update, updated_at: new Date().toISOString() })
    .eq("segment_key", key)
    .select()
    .single();
  if (dbErr) return apiError("INTERNAL", dbErr.message, 500);

  await db.from("audit_logs").insert({
    actor_id: null,
    action: `config.segment.${key}`,
    entity: "monitor_segments",
    entity_id: key,
    before: { min_alert_score: before.min_alert_score, enabled: before.enabled },
    after: { min_alert_score: after.min_alert_score, enabled: after.enabled },
  });

  return apiOk({ segment: after });
}
