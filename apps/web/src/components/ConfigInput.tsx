"use client";

import { useState } from "react";

export function ConfigInput({
  label,
  hint,
  value: initial,
  min,
  max,
  step,
  suffix,
  apiKey,
}: {
  label: string;
  hint?: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
  apiKey: string;
}) {
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setError(null);
    setSaved(false);
    const res = await fetch("/api/config/update", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ key: apiKey, value }),
    });
    if (res.ok) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } else {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? `HTTP ${res.status}`);
    }
    setBusy(false);
  }

  return (
    <div className="toggle-wrap">
      <div style={{ flex: 1 }}>
        <div className="toggle-label">{label}</div>
        {hint && <div className="toggle-hint">{hint}</div>}
        {error && <div className="toggle-hint" style={{ color: "var(--danger)" }}>{error}</div>}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <input
          type="number"
          value={value}
          onChange={(e) => setValue(Number(e.target.value))}
          min={min}
          max={max}
          step={step}
          style={{
            width: 80,
            padding: "6px 10px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border)",
            background: "var(--surface-elevated)",
            color: "var(--text)",
            fontSize: 13,
            textAlign: "right",
          }}
        />
        {suffix && <span className="muted text-sm">{suffix}</span>}
        <button className="btn primary" onClick={save} disabled={busy} style={{ padding: "6px 12px", fontSize: 12 }}>
          {busy ? "..." : saved ? "✓" : "Save"}
        </button>
      </div>
    </div>
  );
}
