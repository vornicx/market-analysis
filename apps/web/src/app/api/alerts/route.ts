import { requireAdmin } from "@/lib/auth";
import { apiOk } from "@/lib/api";
import { createSupabaseServer } from "@/lib/supabase/server";

export async function GET(req: Request) {
  const { error } = await requireAdmin();
  if (error) return error;

  const url = new URL(req.url);
  const segment = url.searchParams.get("segment");
  const band = url.searchParams.get("band");
  const minScore = url.searchParams.get("minScore");
  const limit = Math.min(Number(url.searchParams.get("limit") ?? 50), 200);

  const supabase = await createSupabaseServer();
  let query = supabase
    .from("alerts")
    .select("*, events(home_team, away_team, commence_time)")
    .order("created_at", { ascending: false })
    .limit(limit);
  if (segment) query = query.eq("segment_key", segment);
  if (band) query = query.eq("confidence_band", band);
  if (minScore) query = query.gte("alert_score", Number(minScore));

  const { data } = await query;
  return apiOk({ alerts: data ?? [] });
}
