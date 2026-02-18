import { Shield } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-gray-800 bg-gray-950 py-8 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-gray-500">
            <Shield className="h-4 w-4" />
            <span className="text-sm">AI Provenance Tracker</span>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>MIT License</span>
            <a
              href="https://github.com/ogulcanaydogan/ai-provenance-tracker"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-gray-300 transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
