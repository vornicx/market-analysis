import { createSupabaseServer } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const supabase = await createSupabaseServer();

  const [{ data: config }, { data: lastRun }, { count: alerts24h }] = await Promise.all([
    supabase.from("monitor_configs").select("*").eq("id", 1).single(),
    supabase.from("worker_runs").select("*").order("started_at", { ascending: false }).limit(1).maybeSingle(),
    supabase
      .from("alerts")
      .select("id", { count: "exact", head: true })
      .gte("created_at", new Date(Date.now() - 24 * 3600_000).toISOString()),
  ]);

  const mode = !config
    ? "UNKNOWN"
    : config.global_pause
      ? "PAUSED"
      : config.world_cup_only_mode
        ? "WORLD CUP ONLY"
        : "NORMAL";

  return (
    <div>
      <h1>Overview</h1>
      {config?.dry_run && (
        <div style={{ background: "#5c4400", padding: 12, borderRadius: 6, marginBottom: 16 }}>
          ⚠ DRY RUN — alerts are computed and stored but NOT sent to Telegram.
        </div>
      )}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <StatCard label="Mode" value={mode} />
        <StatCard label="Alerts (24h)" value={String(alerts24h ?? 0)} />
        <StatCard
          label="Worker last seen"
          value={lastRun ? new Date(lastRun.started_at).toLocaleString() : "never"}
        />
        <StatCard
          label="Football / World Cup"
          value={`${config?.football_enabled ? "ON" : "off"} / ${config?.world_cup_enabled ? "ON" : "off"}`}
        />
      </div>
      <p style={{ marginTop: 24, color: "#888" }}>
        Latest alerts appear on the <a href="/alerts" style={{ color: "#9ecbff" }}>Alerts</a> page.
      </p>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: "1px solid #2a2d34", borderRadius: 8, padding: 16, minWidth: 180 }}>
      <div style={{ color: "#888", fontSize: 13 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>{value}</div>
    </div>
  );
}
