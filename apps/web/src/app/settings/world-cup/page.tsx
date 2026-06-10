import { createSupabaseServer } from "@/lib/supabase/server";
import { FlagToggle } from "@/components/FlagToggle";

export const dynamic = "force-dynamic";

export default async function WorldCupSettingsPage() {
  const supabase = await createSupabaseServer();
  const [{ data: config }, { data: segment }] = await Promise.all([
    supabase.from("monitor_configs").select("*").eq("id", 1).single(),
    supabase.from("monitor_segments").select("*").eq("segment_key", "world_cup").single(),
  ]);

  return (
    <div>
      <h1>🏆 World Cup Settings</h1>
      <FlagToggle flag="world_cup_enabled" label="World Cup monitoring enabled" initial={!!config?.world_cup_enabled} />
      <FlagToggle
        flag="world_cup_only_mode"
        label="World Cup ONLY mode"
        initial={!!config?.world_cup_only_mode}
        warning="When enabled, general football monitoring is suppressed even if football_enabled is on. 100% of the API budget goes to World Cup events."
      />

      <h2>Segment configuration</h2>
      <pre style={{ background: "#16181d", padding: 12, borderRadius: 8, fontSize: 12, overflow: "auto" }}>
        {JSON.stringify(segment, null, 2)}
      </pre>
    </div>
  );
}
