"use client";

import { useState } from "react";
import { createBrowserClient } from "@supabase/ssr";

export default function LoginPage() {
  const [email, setEmail] = useState("");
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
    <form onSubmit={signIn} style={{ maxWidth: 320, margin: "10vh auto" }}>
      <h1>Sign in</h1>
      <input
        type="email" placeholder="email" value={email} required
        onChange={(e) => setEmail(e.target.value)}
        style={{ display: "block", width: "100%", marginBottom: 8, padding: 8 }}
      />
      <input
        type="password" placeholder="password" value={password} required
        onChange={(e) => setPassword(e.target.value)}
        style={{ display: "block", width: "100%", marginBottom: 8, padding: 8 }}
      />
      <button disabled={busy} style={{ padding: "8px 16px" }}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
      {error && <p style={{ color: "#ff7b7b" }}>{error}</p>}
    </form>
  );
}
