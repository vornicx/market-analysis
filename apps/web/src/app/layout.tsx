import type { ReactNode } from "react";
import Link from "next/link";

export const metadata = {
  title: "Market Monitor",
  description: "Football odds market monitoring — control plane",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/alerts", label: "Alerts" },
  { href: "/settings/football", label: "Football" },
  { href: "/settings/world-cup", label: "World Cup" },
  { href: "/feedback", label: "Feedback" },
  { href: "/status", label: "Status" },
  { href: "/audit", label: "Audit" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, background: "#0f1115", color: "#e6e6e6" }}>
        <div style={{ display: "flex", minHeight: "100vh" }}>
          <nav style={{ width: 200, padding: 16, borderRight: "1px solid #2a2d34" }}>
            <div style={{ fontWeight: 700, marginBottom: 16 }}>⚽ Market Monitor</div>
            {NAV.map((item) => (
              <div key={item.href} style={{ marginBottom: 8 }}>
                <Link href={item.href} style={{ color: "#9ecbff", textDecoration: "none" }}>
                  {item.label}
                </Link>
              </div>
            ))}
          </nav>
          <main style={{ flex: 1, padding: 24 }}>{children}</main>
        </div>
      </body>
    </html>
  );
}
