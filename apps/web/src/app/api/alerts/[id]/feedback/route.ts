import { z } from "zod";
import { FEEDBACK_VERDICTS } from "@market-monitor/shared";
import { apiError, apiOk } from "@/lib/api";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

const bodySchema = z.object({
  verdict: z.enum(FEEDBACK_VERDICTS),
  note: z.string().max(500).optional(),
});

export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  const parsed = bodySchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return apiError("VALIDATION", "verdict must be useful|noise|late|wrong", 422);

  const db = createSupabaseAdmin();
  const { data, error: dbErr } = await db
    .from("alert_feedback")
    .upsert(
      { alert_id: id, verdict: parsed.data.verdict, note: parsed.data.note ?? null },
      { onConflict: "alert_id,user_id" }
    )
    .select()
    .single();
  if (dbErr) return apiError("INTERNAL", dbErr.message, 500);
  return apiOk({ feedback: data }, 201);
}
