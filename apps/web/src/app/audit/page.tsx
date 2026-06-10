import { createSupabaseServer } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const supabase = await createSupabaseServer();
  const { data: logs } = await supabase
    .from("audit_logs")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100);

  return (
    <div>
      <h1>Audit log</h1>
      {!logs?.length ? (
        <p style={{ color: "#888" }}>No changes recorded.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "#888" }}>
              <th>Time</th><th>Actor</th><th>Action</th><th>Entity</th><th>Change</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} style={{ borderTop: "1px solid #2a2d34" }}>
                <td>{new Date(l.created_at).toLocaleString()}</td>
                <td>{l.actor_id ?? "worker"}</td>
                <td>{l.action}</td>
                <td>{l.entity}{l.entity_id ? `:${l.entity_id}` : ""}</td>
                <td>
                  <code style={{ fontSize: 11 }}>
                    {JSON.stringify(l.before)} → {JSON.stringify(l.after)}
                  </code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
