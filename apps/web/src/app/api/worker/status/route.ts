import { requireAdmin } from "@/lib/auth";
import { apiOk } from "@/lib/api";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

export async function GET() {
  const { error } = await requireAdmin();
  if (error) return error;

  const db = createSupabaseAdmin();
  const [{ data: lastRun }, { data: config }] = await Promise.all([
    db.from("worker_runs").select("*").order("started_at", { ascending: false }).limit(1).maybeSingle(),
    db.from("monitor_configs").select("*").eq("id", 1).single(),
  ]);

  const resolvedMode = !config
    ? "UNKNOWN"
    : config.global_pause
      ? "PAUSED"
      : config.world_cup_only_mode
        ? "WORLD_CUP_ONLY"
        : "NORMAL";

  const heartbeatAgeSeconds = lastRun
    ? Math.round((Date.now() - new Date(lastRun.started_at).getTime()) / 1000)
    : null;

  return apiOk({ lastRun, heartbeatAgeSeconds, resolvedMode, dryRun: config?.dry_run ?? null });
}
