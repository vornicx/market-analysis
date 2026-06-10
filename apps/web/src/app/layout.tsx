import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";

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
      <body>
        <div style={{ display: "flex", minHeight: "100vh" }}>
          <nav className="nav">
            <div className="brand">⚽ Market Monitor</div>
            {NAV.map((item) => (
              <div key={item.href} className="item">
                <Link href={item.href}>{item.label}</Link>
              </div>
            ))}
          </nav>
          <main style={{ flex: 1, padding: 24, maxWidth: 1200 }}>{children}</main>
        </div>
      </body>
    </html>
  );
}
