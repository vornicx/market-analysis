import { createSupabaseAdmin } from "@/lib/supabase/admin";
import { FlagToggle } from "@/components/FlagToggle";

export const dynamic = "force-dynamic";

export default async function WorldCupSettingsPage() {
  const supabase = createSupabaseAdmin();
  const [{ data: config }, { data: segment }] = await Promise.all([
    supabase.from("monitor_configs").select("*").eq("id", 1).single(),
    supabase.from("monitor_segments").select("*").eq("segment_key", "world_cup").single(),
  ]);

  const flags = [
    { flag: "world_cup_enabled" as const, label: "World Cup monitoring enabled" },
    {
      flag: "world_cup_only_mode" as const,
      label: "World Cup ONLY mode",
      hint: "General football monitoring is suppressed. 100% of API budget goes to World Cup events.",
    },
  ];

  return (
    <div>
      <h1>🏆 World Cup Settings</h1>

      <div style={{ marginBottom: 20 }}>
        {flags.map((f) => (
          <FlagToggle key={f.flag} flag={f.flag} label={f.label} hint={f.hint} initial={!!config?.[f.flag]} />
        ))}
      </div>

      <h2>Segment configuration</h2>
      <div className="table-wrap">
        <pre className="panel" style={{ margin: 0, border: "none", borderRadius: 0 }}>
          {JSON.stringify(segment, null, 2)}
        </pre>
      </div>
    </div>
  );
}
