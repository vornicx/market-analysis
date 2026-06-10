import { z } from "zod";
import { TOGGLEABLE_FLAGS } from "@market-monitor/shared";
import { requireAdmin } from "@/lib/auth";
import { apiError, apiOk } from "@/lib/api";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

const bodySchema = z.object({
  flag: z.enum(TOGGLEABLE_FLAGS),
  value: z.boolean(),
});

export async function POST(req: Request) {
  const { user, error } = await requireAdmin();
  if (error) return error;

  const parsed = bodySchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return apiError("VALIDATION", "Body must be { flag, value }", 422);
  const { flag, value } = parsed.data;

  const db = createSupabaseAdmin();
  const { data: before } = await db.from("monitor_configs").select("*").eq("id", 1).single();
  const { data: after, error: dbErr } = await db
    .from("monitor_configs")
    .update({ [flag]: value, updated_by: user!.id, updated_at: new Date().toISOString() })
    .eq("id", 1)
    .select()
    .single();
  if (dbErr) return apiError("INTERNAL", dbErr.message, 500);

  await db.from("audit_logs").insert({
    actor_id: user!.id,
    action: `config.toggle.${flag}`,
    entity: "monitor_configs",
    entity_id: "1",
    before: { [flag]: before?.[flag] },
    after: { [flag]: value },
  });

  const resolvedMode = after.global_pause
    ? "PAUSED"
    : after.world_cup_only_mode
      ? "WORLD_CUP_ONLY"
      : "NORMAL";
  return apiOk({ config: after, resolvedMode });
}
