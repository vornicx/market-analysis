import { z } from "zod";
import { apiError, apiOk } from "@/lib/api";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  const db = createSupabaseAdmin();
  const { data } = await db
    .from("alerts")
    .select("*, events(*), alert_evidence(payload), llm_analyses(*), telegram_deliveries(*), alert_feedback(*)")
    .eq("id", id)
    .maybeSingle();
  if (!data) return apiError("NOT_FOUND", "Alert not found", 404);
  return apiOk({ alert: data });
}

const patchSchema = z.object({ status: z.enum(["acknowledged", "dismissed"]) });

export async function PATCH(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  const parsed = patchSchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return apiError("VALIDATION", "status must be acknowledged|dismissed", 422);

  const db = createSupabaseAdmin();
  const { data, error: dbErr } = await db
    .from("alerts")
    .update({ status: parsed.data.status })
    .eq("id", id)
    .select()
    .maybeSingle();
  if (dbErr) return apiError("INTERNAL", dbErr.message, 500);
  if (!data) return apiError("NOT_FOUND", "Alert not found", 404);
  return apiOk({ alert: data });
}
