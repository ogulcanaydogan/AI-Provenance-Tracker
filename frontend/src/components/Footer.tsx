import Link from "next/link";
import { Shield, Github } from "lucide-react";

export default function Footer() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  return (
    <footer className="border-t border-[#262626] py-10 mt-16">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Shield className="h-4 w-4 text-blue-400" />
              <span className="font-semibold text-white text-sm">AI Provenance Tracker</span>
            </div>
            <p className="text-gray-600 text-xs leading-relaxed">
              Open-source multi-modal AI content detection with explainable scoring.
            </p>
          </div>

          {/* Detection */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Detection
            </h4>
            <ul className="space-y-2">
              <li>
                <Link href="/detect/text" className="text-gray-500 hover:text-white transition-colors text-sm">
                  Text Detection
                </Link>
              </li>
              <li>
                <Link href="/detect/image" className="text-gray-500 hover:text-white transition-colors text-sm">
                  Image Detection
                </Link>
              </li>
              <li>
                <Link href="/detect/audio" className="text-gray-500 hover:text-white transition-colors text-sm">
                  Audio Detection
                </Link>
              </li>
              <li>
                <Link href="/detect/video" className="text-gray-500 hover:text-white transition-colors text-sm">
                  Video Detection
                </Link>
              </li>
            </ul>
          </div>

          {/* Platform */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Platform
            </h4>
            <ul className="space-y-2">
              <li>
                <Link href="/dashboard" className="text-gray-500 hover:text-white transition-colors text-sm">
                  Dashboard
                </Link>
              </li>
              <li>
                <Link href="/history" className="text-gray-500 hover:text-white transition-colors text-sm">
                  History
                </Link>
              </li>
              <li>
                <Link
                  href={`${apiUrl}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-500 hover:text-white transition-colors text-sm"
                >
                  API Docs
                </Link>
              </li>
            </ul>
          </div>

          {/* Project */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Project
            </h4>
            <ul className="space-y-2">
              <li>
                <Link
                  href="https://github.com/ogulcanaydogan/ai-provenance-tracker"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-gray-500 hover:text-white transition-colors text-sm"
                >
                  <Github className="h-3.5 w-3.5" />
                  GitHub
                </Link>
              </li>
              <li>
                <Link
                  href="https://github.com/ogulcanaydogan/ai-provenance-tracker/blob/main/CONTRIBUTING.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-500 hover:text-white transition-colors text-sm"
                >
                  Contributing
                </Link>
              </li>
              <li>
                <Link
                  href="https://github.com/ogulcanaydogan/ai-provenance-tracker/blob/main/LICENSE"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-500 hover:text-white transition-colors text-sm"
                >
                  MIT License
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-[#1a1a1a] pt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-gray-600 text-xs">
            Built by{" "}
            <Link
              href="https://ogulcanaydogan.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-white transition-colors"
            >
              Ogulcan Aydogan
            </Link>
          </p>
          <p className="text-gray-700 text-xs">
            AI detection is not 100% accurate. Use results as one signal in content verification.
          </p>
        </div>
      </div>
    </footer>
  );
}
