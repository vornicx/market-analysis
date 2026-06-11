import { createSupabaseAdmin } from "@/lib/supabase/admin";
import { FlagToggle } from "@/components/FlagToggle";

export const dynamic = "force-dynamic";

export default async function FootballSettingsPage() {
  const supabase = createSupabaseAdmin();
  const [{ data: config }, { data: segment }] = await Promise.all([
    supabase.from("monitor_configs").select("*").eq("id", 1).single(),
    supabase.from("monitor_segments").select("*").eq("segment_key", "general_football").single(),
  ]);

  const flags = [
    { flag: "football_enabled" as const, label: "Football monitoring enabled" },
    { flag: "dry_run" as const, label: "Dry run (no Telegram sends)", hint: "Alerts are computed but not delivered" },
    { flag: "global_pause" as const, label: "Global pause (worker idles)", hint: "Worker stops all monitoring" },
  ];

  return (
    <div>
      <h1>⚽ General Football Settings</h1>

      <div style={{ marginBottom: 20 }}>
        {flags.map((f) => (
          <FlagToggle key={f.flag} flag={f.flag} label={f.label} hint={f.hint} initial={!!config?.[f.flag]} />
        ))}
      </div>

      <h2>Segment configuration</h2>
      <p className="muted text-sm" style={{ marginBottom: 12 }}>
        Edited via PATCH /api/config/segments/general_football — full form UI is a 14-day-plan item; current values below.
      </p>
      <div className="table-wrap">
        <pre className="panel" style={{ margin: 0, border: "none", borderRadius: 0 }}>
          {JSON.stringify(segment, null, 2)}
        </pre>
      </div>
    </div>
  );
}
