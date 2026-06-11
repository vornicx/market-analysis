"use client";

import { useState } from "react";
import type { MonitorSegment } from "@market-monitor/shared";

export function SegmentEditor({ segment: initial }: { segment: MonitorSegment }) {
  const [segment, setSegment] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  async function save(changes: Record<string, any>) {
    setBusy(true);
    setMsg(null);
    const res = await fetch(`/api/config/segments/${segment.segment_key}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(changes),
    });
    if (res.ok) {
      const data = await res.json();
      setSegment(data.segment);
      setMsg({ type: "ok", text: "Saved" });
      setTimeout(() => setMsg(null), 2000);
    } else {
      const body = await res.json().catch(() => null);
      setMsg({ type: "error", text: body?.error?.message ?? "Error" });
    }
    setBusy(false);
  }

  const segLabel = segment.segment_key === "world_cup" ? "🏆 World Cup" : "⚽ General Football";

  return (
    <div className="card" style={{ padding: 0 }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{segLabel}</div>
          <div className="muted text-sm">{segment.display_label} — {segment.sport_keys.join(", ")}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="text-sm muted">
            {segment.enabled ? <span style={{ color: "var(--ok)" }}>● Enabled</span> : <span style={{ color: "var(--text-secondary)" }}>○ Disabled</span>}
          </span>
          <button className="btn" onClick={() => save({ enabled: !segment.enabled })} disabled={busy}>
            Toggle
          </button>
        </div>
      </div>

      <div style={{ padding: "16px 20px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <div className="muted text-sm" style={{ marginBottom: 4 }}>Min Alert Score</div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="number"
              defaultValue={segment.min_alert_score}
              min={0}
              max={100}
              onBlur={(e) => save({ min_alert_score: Number(e.target.value) })}
              style={{ width: 70, padding: "6px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", background: "var(--surface-elevated)", color: "var(--text)", fontSize: 13, textAlign: "right" }}
            />
            <span className="muted text-sm">/ 100</span>
            <button className="btn" style={{ padding: "4px 10px", fontSize: 11 }} onClick={() => save({ min_alert_score: segment.min_alert_score })} disabled={busy}>
              Save
            </button>
          </div>
        </div>
        <div>
          <div className="muted text-sm" style={{ marginBottom: 4 }}>Chat ID</div>
          <code style={{ fontSize: 12, color: "var(--text-secondary)" }}>{segment.telegram_chat_id ?? "—"}</code>
        </div>
      </div>

      <details style={{ borderTop: "1px solid var(--border)" }}>
        <summary style={{ padding: "12px 20px", cursor: "pointer", fontWeight: 500, fontSize: 13, color: "var(--text-secondary)" }}>
          Thresholds
        </summary>
        <div style={{ padding: "0 20px 16px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {Object.entries(segment.thresholds).map(([key, val]) => (
            <div key={key} style={{ background: "var(--surface-elevated)", borderRadius: "var(--radius-sm)", padding: 10 }}>
              <div className="muted text-sm" style={{ marginBottom: 4, fontWeight: 600 }}>{key}</div>
              {Object.entries(val as Record<string, number>).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "2px 0" }}>
                  <span className="muted">{k}</span>
                  <span>{v}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </details>

      <details style={{ borderTop: "1px solid var(--border)" }}>
        <summary style={{ padding: "12px 20px", cursor: "pointer", fontWeight: 500, fontSize: 13, color: "var(--text-secondary)" }}>
          Polling Profile
        </summary>
        <div style={{ padding: "0 20px 16px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {Object.entries(segment.polling_profile).map(([key, val]) => (
            <div key={key} style={{ background: "var(--surface-elevated)", borderRadius: "var(--radius-sm)", padding: 10 }}>
              <div className="muted text-sm" style={{ marginBottom: 4 }}>{key}</div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  type="number"
                  defaultValue={val}
                  min={0}
                  max={9999}
                  onBlur={(e) => {
                    const newVal = Number(e.target.value);
                    save({ polling_profile: { [key]: newVal } });
                  }}
                  style={{ width: 70, padding: "4px 8px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)", fontSize: 12, textAlign: "right" }}
                />
                <span className="muted text-sm">sec</span>
              </div>
            </div>
          ))}
        </div>
      </details>

      {msg && (
        <div style={{ padding: "8px 20px", borderTop: "1px solid var(--border)" }}>
          <span className="text-sm" style={{ color: msg.type === "ok" ? "var(--ok)" : "var(--danger)" }}>{msg.text}</span>
        </div>
      )}
    </div>
  );
}
