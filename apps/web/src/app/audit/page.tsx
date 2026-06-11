import { createSupabaseAdmin } from "@/lib/supabase/admin";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const supabase = createSupabaseAdmin();
  const { data: logs } = await supabase
    .from("audit_logs")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100);

  return (
    <div>
      <h1>Audit Log</h1>
      {!logs?.length ? (
        <div className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <p className="muted">No changes recorded.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th><th>Actor</th><th>Action</th><th>Entity</th><th>Change</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td className="muted text-sm">{new Date(l.created_at).toLocaleString()}</td>
                  <td>
                    <code style={{ color: l.actor_id ? undefined : "var(--text-secondary)" }}>
                      {l.actor_id?.slice(0, 8) ?? "worker"}
                    </code>
                  </td>
                  <td><span className="pill" style={{ background: "var(--surface-elevated)" }}>{l.action}</span></td>
                  <td className="muted">{l.entity}{l.entity_id ? `:${l.entity_id.slice(0, 8)}` : ""}</td>
                  <td>
                    <pre className="panel" style={{ margin: 0, padding: "4px 8px", fontSize: 10, maxWidth: 300 }}>
                      {JSON.stringify(l.before)} → {JSON.stringify(l.after)}
                    </pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
