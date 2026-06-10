"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createBrowserClient } from "@supabase/ssr";

/** Subscribes to new alerts via Supabase Realtime and refreshes the page data. */
export function RealtimeAlerts() {
  const router = useRouter();
  const [incoming, setIncoming] = useState(0);

  useEffect(() => {
    const supabase = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
    const channel = supabase
      .channel("alerts-feed")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "alerts" },
        () => {
          setIncoming((n) => n + 1);
          router.refresh();
        }
      )
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [router]);

  if (incoming === 0) return null;
  return (
    <div className="banner info">
      🔔 {incoming} new alert{incoming > 1 ? "s" : ""} arrived live
    </div>
  );
}
