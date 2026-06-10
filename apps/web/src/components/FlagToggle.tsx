"use client";

import { useState } from "react";
import type { ToggleableFlag } from "@market-monitor/shared";

export function FlagToggle({
  flag,
  label,
  initial,
  warning,
}: {
  flag: ToggleableFlag;
  label: string;
  initial: boolean;
  warning?: string;
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
    <div style={{ margin: "12px 0" }}>
      <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
        <input type="checkbox" checked={value} disabled={busy} onChange={toggle} />
        <span>{label}</span>
        <code style={{ color: "#888" }}>{flag}</code>
      </label>
      {value && warning && <p style={{ color: "#ffc66d", margin: "4px 0 0 24px" }}>{warning}</p>}
      {error && <p style={{ color: "#ff7b7b", margin: "4px 0 0 24px" }}>{error}</p>}
    </div>
  );
}
