import { apiOk } from "@/lib/api";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

export async function GET() {
  let db = false;
  try {
    const { error } = await createSupabaseAdmin()
      .from("monitor_configs")
      .select("id", { head: true, count: "exact" })
      .eq("id", 1);
    db = !error;
  } catch {
    db = false;
  }
  return apiOk({ ok: db, db });
}
