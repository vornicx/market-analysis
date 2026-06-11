import { createSupabaseAdmin } from "@/lib/supabase/admin";
import { FlagToggle } from "@/components/FlagToggle";
import { ConfigInput } from "@/components/ConfigInput";
import { SegmentEditor } from "./SegmentEditor";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const supabase = createSupabaseAdmin();
  const [{ data: config }, { data: segments }] = await Promise.all([
    supabase.from("monitor_configs").select("*").eq("id", 1).single(),
    supabase.from("monitor_segments").select("*").order("segment_key"),
  ]);

  return (
    <div>
      <h1>Settings</h1>

      <h2>Global Controls</h2>
      <div style={{ marginBottom: 20 }}>
        <FlagToggle flag="global_pause" label="Global Pause" initial={!!config?.global_pause} hint="Worker stops all monitoring" />
        <FlagToggle flag="dry_run" label="Dry Run" initial={!!config?.dry_run} hint="Alerts computed but NOT sent to Telegram" warning="Alerts will not be delivered while enabled" />
        <FlagToggle flag="world_cup_only_mode" label="World Cup Only Mode" initial={!!config?.world_cup_only_mode} hint="100% of API budget goes to World Cup events" />
        <FlagToggle flag="llm_enabled" label="LLM Analysis" initial={!!config?.llm_enabled} hint="Annotate alerts via AI (requires OpenCode Go key)" />
      </div>

      <h2>Credit Limits</h2>
      <div style={{ marginBottom: 20 }}>
        <ConfigInput label="Daily Credit Cap" hint="Max API credits per day" value={config?.daily_credit_cap ?? 16} min={1} max={100} step={1} suffix="credits" apiKey="daily_credit_cap" />
        <ConfigInput label="Monthly Credit Cap" hint="Max API credits per month" value={config?.monthly_credit_cap ?? 450} min={1} max={1000} step={10} suffix="credits" apiKey="monthly_credit_cap" />
      </div>

      <h2>Worker Settings</h2>
      <div style={{ marginBottom: 20 }}>
        <ConfigInput label="Poll Floor" hint="Minimum seconds between poll cycles" value={config?.worker_poll_floor_seconds ?? 300} min={30} max={3600} step={30} suffix="sec" apiKey="worker_poll_floor_seconds" />
        <ConfigInput label="Alert Suppression" hint="Minutes before same alert can fire again" value={config?.alert_suppression_minutes ?? 90} min={0} max={1440} step={10} suffix="min" apiKey="alert_suppression_minutes" />
      </div>

      <h2>Segments</h2>
      {segments?.length ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {segments.map((seg) => (
            <SegmentEditor key={seg.segment_key} segment={seg} />
          ))}
        </div>
      ) : (
        <p className="muted">No segments found.</p>
      )}
    </div>
  );
}
