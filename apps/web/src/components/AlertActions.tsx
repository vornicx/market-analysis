"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { FeedbackVerdict } from "@market-monitor/shared";

const VERDICTS: { value: FeedbackVerdict; label: string }[] = [
  { value: "useful", label: "👍 Useful" },
  { value: "noise", label: "🔇 Noise" },
  { value: "late", label: "⏰ Late" },
  { value: "wrong", label: "❌ Wrong" },
];

export function AlertActions({ alertId, status }: { alertId: string; status: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function call(path: string, init: RequestInit, action: string) {
    setBusy(action);
    setMessage(null);
    const res = await fetch(path, {
      headers: { "content-type": "application/json" },
      ...init,
    });
    if (res.ok) {
      setMessage(`✓ ${action}`);
      router.refresh();
    } else {
      const body = await res.json().catch(() => null);
      setMessage(body?.error?.message ?? `Error ${res.status}`);
    }
    setBusy(null);
  }

  return (
    <div style={{ margin: "16px 0" }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {status === "new" && (
          <button
            className="btn primary"
            disabled={!!busy}
            onClick={() =>
              call(`/api/alerts/${alertId}`, { method: "PATCH", body: JSON.stringify({ status: "acknowledged" }) }, "acknowledged")
            }
          >
            Acknowledge
          </button>
        )}
        {status !== "dismissed" && (
          <button
            className="btn danger"
            disabled={!!busy}
            onClick={() =>
              call(`/api/alerts/${alertId}`, { method: "PATCH", body: JSON.stringify({ status: "dismissed" }) }, "dismissed")
            }
          >
            Dismiss
          </button>
        )}
        <button
          className="btn"
          disabled={!!busy}
          title="Re-run detectors on stored snapshots with current thresholds (0 API credits)"
          onClick={() => call(`/api/alerts/${alertId}/replay`, { method: "POST" }, "replay queued")}
        >
          🔁 Replay
        </button>
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        {VERDICTS.map((v) => (
          <button
            key={v.value}
            className="btn"
            disabled={!!busy}
            onClick={() =>
              call(`/api/alerts/${alertId}/feedback`, { method: "POST", body: JSON.stringify({ verdict: v.value }) }, `feedback: ${v.value}`)
            }
          >
            {v.label}
          </button>
        ))}
      </div>
      {message && <p className="muted" style={{ marginTop: 8 }}>{message}</p>}
    </div>
  );
}
