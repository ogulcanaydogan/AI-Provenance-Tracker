"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X, FileText, Image, Mic, Video, BarChart3, Github } from "lucide-react";

const NAV_LINKS = [
  { href: "/detect/text", label: "Text", icon: FileText },
  { href: "/detect/image", label: "Image", icon: Image },
  { href: "/detect/audio", label: "Audio", icon: Mic },
  { href: "/detect/video", label: "Video", icon: Video },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
];

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="border-b border-[#262626] sticky top-0 z-50 bg-[#0a0a0a]/80 backdrop-blur-md">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between max-w-6xl">
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <span className="text-xl">🔍</span>
          <span className="font-bold text-lg">AI Provenance</span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-5">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-gray-400 hover:text-white transition-colors text-sm"
            >
              {link.label}
            </Link>
          ))}
          <span className="w-px h-4 bg-[#333]" />
          <Link
            href="https://github.com/ogulcanaydogan/ai-provenance-tracker"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="GitHub"
          >
            <Github className="h-4 w-4" />
          </Link>
        </nav>

        {/* Mobile Toggle */}
        <button
          className="md:hidden text-gray-400 hover:text-white transition-colors p-1"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile Nav */}
      {mobileOpen && (
        <nav className="md:hidden border-t border-[#262626] bg-[#0a0a0a]">
          <div className="container mx-auto px-4 py-3 flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#171717] transition-colors text-sm"
              >
                <link.icon className="h-4 w-4" />
                {link.label}
              </Link>
            ))}
            <div className="border-t border-[#262626] my-1" />
            <Link
              href="https://github.com/ogulcanaydogan/ai-provenance-tracker"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#171717] transition-colors text-sm"
            >
              <Github className="h-4 w-4" />
              GitHub
            </Link>
          </div>
        </nav>
      )}
    </header>
  );
}
