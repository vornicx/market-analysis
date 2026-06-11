import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "Market Monitor",
  description: "Football odds market monitoring — control plane",
};

const NAV = [
  { href: "/", label: "Overview", icon: "◉" },
  { href: "/alerts", label: "Alerts", icon: "⚡" },
  { href: "/settings", label: "Settings", icon: "⚙" },
  { href: "/settings/football", label: "Football", icon: "⚽" },
  { href: "/settings/world-cup", label: "World Cup", icon: "🏆" },
  { href: "/feedback", label: "Feedback", icon: "✎" },
  { href: "/status", label: "Status", icon: "◷" },
  { href: "/audit", label: "Audit", icon: "📋" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="layout">
          <nav className="sidebar">
            <div className="sidebar-brand">
              <span className="logo">M</span>
              Market Monitor
            </div>
            {NAV.map((item) => (
              <Link key={item.href} href={item.href} className="sidebar-link">
                <span className="icon">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </nav>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
