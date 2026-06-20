import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Agent OS Dashboard",
  description: "Live monitoring for the autonomous multi-agent company",
};

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/brain", label: "Brain" },
  { href: "/history", label: "History" },
  { href: "/approvals", label: "Approvals" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistMono.variable} h-full antialiased dark`}>
      <body className="min-h-full flex bg-gray-950 text-gray-100 font-mono">
        <nav className="w-48 bg-gray-900 border-r border-gray-800 p-4 flex flex-col gap-1">
          <div className="text-lg font-bold text-white mb-4">Agent OS</div>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="px-3 py-2 rounded text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </body>
    </html>
  );
}
