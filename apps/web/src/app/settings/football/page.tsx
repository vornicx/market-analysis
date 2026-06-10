import { createSupabaseServer } from "@/lib/supabase/server";
import { FlagToggle } from "@/components/FlagToggle";

export const dynamic = "force-dynamic";

export default async function FootballSettingsPage() {
  const supabase = await createSupabaseServer();
  const [{ data: config }, { data: segment }] = await Promise.all([
    supabase.from("monitor_configs").select("*").eq("id", 1).single(),
    supabase.from("monitor_segments").select("*").eq("segment_key", "general_football").single(),
  ]);

  return (
    <div>
      <h1>⚽ General Football Settings</h1>
      <FlagToggle flag="football_enabled" label="Football monitoring enabled" initial={!!config?.football_enabled} />
      <FlagToggle flag="dry_run" label="Dry run (no Telegram sends)" initial={!!config?.dry_run} />
      <FlagToggle flag="global_pause" label="Global pause (worker idles)" initial={!!config?.global_pause} />

      <h2>Segment configuration</h2>
      <p style={{ color: "#888" }}>
        Edited via PATCH /api/config/segments/general_football — full form UI is a
        14-day-plan item; current values below.
      </p>
      <pre style={{ background: "#16181d", padding: 12, borderRadius: 8, fontSize: 12, overflow: "auto" }}>
        {JSON.stringify(segment, null, 2)}
      </pre>
    </div>
  );
}
