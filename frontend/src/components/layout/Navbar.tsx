"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, Github } from "lucide-react";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/detect/text", label: "Text Detection" },
  { href: "/detect/image", label: "Image Detection" },
  { href: "/detect/audio", label: "Audio Detection" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/history", label: "History" },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center gap-2">
            <Shield className="h-7 w-7 text-blue-500" />
            <span className="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              AI Provenance Tracker
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  pathname === link.href
                    ? "bg-gray-800 text-white"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <a
            href="https://github.com/ogulcanaydogan/ai-provenance-tracker"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-700 text-sm text-gray-300 hover:text-white hover:border-gray-500 transition-colors"
          >
            <Github className="h-4 w-4" />
            <span className="hidden sm:inline">Star on GitHub</span>
          </a>
        </div>
      </div>
    </nav>
  );
}
