"use client";

import { useState } from "react";
import type { ToggleableFlag } from "@market-monitor/shared";

export function FlagToggle({
  flag,
  label,
  initial,
  warning,
  hint,
}: {
  flag: ToggleableFlag;
  label: string;
  initial: boolean;
  warning?: string;
  hint?: string;
}) {
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    setBusy(true);
    setError(null);
    const res = await fetch("/api/config/toggle", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ flag, value: !value }),
    });
    if (res.ok) {
      setValue(!value);
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
        {warning && value && <div className="toggle-hint" style={{ color: "var(--warn)" }}>{warning}</div>}
        {error && <div className="toggle-hint" style={{ color: "var(--danger)" }}>{error}</div>}
      </div>
      <label className="toggle">
        <input type="checkbox" checked={value} disabled={busy} onChange={toggle} />
        <span className="slider" />
      </label>
    </div>
  );
}
