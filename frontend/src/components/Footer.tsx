import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-[#262626] py-8 mt-16">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-gray-500 text-sm">
            Built by{" "}
            <Link
              href="https://ogulcanaydogan.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-white transition-colors"
            >
              Ogulcan Aydogan
            </Link>
          </p>

          <div className="flex items-center gap-6 text-sm">
            <Link
              href="https://github.com/ogulcanaydogan/ai-provenance-tracker"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-white transition-colors"
            >
              GitHub
            </Link>
            <Link
              href="/api"
              className="text-gray-500 hover:text-white transition-colors"
            >
              API
            </Link>
            <Link
              href="/privacy"
              className="text-gray-500 hover:text-white transition-colors"
            >
              Privacy
            </Link>
          </div>
        </div>

        <p className="text-gray-600 text-xs text-center mt-6">
          Disclaimer: AI detection is not 100% accurate. Results should be used as one data point in content verification.
        </p>
      </div>
    </footer>
  );
}
