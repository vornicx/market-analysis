"use client";

import { useState } from "react";
import { createBrowserClient } from "@supabase/ssr";

export default function LoginPage() {
  const [email, setEmail] = useState("vornicx@gmail.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function signIn(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const supabase = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setError(error.message);
      setBusy(false);
    } else {
      window.location.href = "/";
    }
  }

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
      <form onSubmit={signIn} style={{ width: "100%", maxWidth: 360 }}>
        <div className="card" style={{ padding: 32 }}>
          <h1 style={{ marginBottom: 24, textAlign: "center" }}>Sign In</h1>

          <div style={{ marginBottom: 16 }}>
            <label className="muted text-sm" style={{ display: "block", marginBottom: 6 }}>Email</label>
            <input
              type="email" value={email} required
              onChange={(e) => setEmail(e.target.value)}
              className="field"
              style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: "var(--radius-sm)", padding: "10px 12px", width: "100%", fontSize: 14, outline: "none" }}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label className="muted text-sm" style={{ display: "block", marginBottom: 6 }}>Password</label>
            <input
              type="password" placeholder="Enter your password" value={password} required
              onChange={(e) => setPassword(e.target.value)}
              style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: "var(--radius-sm)", padding: "10px 12px", width: "100%", fontSize: 14, outline: "none" }}
              autoFocus
            />
          </div>

          {error && <div className="banner danger" style={{ marginBottom: 16 }}>{error}</div>}

          <button
            disabled={busy}
            className="btn primary"
            style={{ width: "100%", justifyContent: "center", padding: "10px 16px", fontSize: 14 }}
          >
            {busy ? "Signing in..." : "Sign In"}
          </button>
        </div>
      </form>
    </div>
  );
}
