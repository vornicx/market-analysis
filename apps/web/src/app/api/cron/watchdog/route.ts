import { NextResponse } from "next/server";
import { createSupabaseAdmin } from "@/lib/supabase/admin";

const STALE_MINUTES = 30;

/**
 * Vercel cron watchdog FOR the worker (not part of the monitoring pipeline).
 * Runs on production only — Vercel crons do not fire on preview deployments.
 * If the worker heartbeat is stale, pings Telegram once per invocation.
 */
export async function GET(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("authorization") !== `Bearer ${secret}`) {
    return NextResponse.json({ error: { code: "FORBIDDEN" } }, { status: 403 });
  }

  const db = createSupabaseAdmin();
  const { data: lastRun } = await db
    .from("worker_runs")
    .select("started_at, status")
    .order("started_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const ageMinutes = lastRun
    ? (Date.now() - new Date(lastRun.started_at).getTime()) / 60000
    : Infinity;

  if (ageMinutes <= STALE_MINUTES) {
    return NextResponse.json({ ok: true, ageMinutes: Math.round(ageMinutes) });
  }

  // Stale — notify via Telegram if the web app has the bot credentials.
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.WATCHDOG_TELEGRAM_CHAT_ID;
  let notified = false;
  if (token && chatId) {
    const text = lastRun
      ? `🚨 Worker heartbeat is ${Math.round(ageMinutes)} min stale (last status: ${lastRun.status}). Check the worker host.`
      : "🚨 Worker has never reported a run. Is it deployed?";
    const resp = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text }),
    });
    notified = resp.ok;
  }

  return NextResponse.json({
    ok: false,
    ageMinutes: ageMinutes === Infinity ? null : Math.round(ageMinutes),
    notified,
  });
}
