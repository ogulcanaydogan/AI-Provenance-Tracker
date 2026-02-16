"use client";

import Link from "next/link";

export default function Header() {
  return (
    <header className="border-b border-[#262626]">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between max-w-6xl">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-2xl">🔍</span>
          <span className="font-bold text-lg">AI Provenance</span>
        </Link>

        <nav className="flex items-center gap-6">
          <Link
            href="/detect/text"
            className="text-gray-400 hover:text-white transition-colors"
          >
            Text
          </Link>
          <Link
            href="/detect/image"
            className="text-gray-400 hover:text-white transition-colors"
          >
            Image
          </Link>
          <Link
            href="/detect/audio"
            className="text-gray-400 hover:text-white transition-colors"
          >
            Audio
          </Link>
          <Link
            href="/detect/video"
            className="text-gray-400 hover:text-white transition-colors"
          >
            Video
          </Link>
          <Link
            href="/dashboard"
            className="text-gray-400 hover:text-white transition-colors"
          >
            Dashboard
          </Link>
          <Link
            href="https://github.com/ogulcanaydogan/ai-provenance-tracker"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-white transition-colors"
          >
            GitHub
          </Link>
          <Link
            href="/docs"
            className="text-gray-400 hover:text-white transition-colors"
          >
            API Docs
          </Link>
        </nav>
      </div>
    </header>
  );
}
