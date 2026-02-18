import Link from "next/link";
import { Shield, ArrowLeft, FileText, Image, Mic, Video } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="flex items-center justify-center mb-6">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <Shield className="h-8 w-8 text-red-400" />
          </div>
        </div>

        <h1 className="text-5xl font-bold text-white mb-3">404</h1>
        <p className="text-gray-400 text-lg mb-8">
          This page does not exist. It may have been moved or removed.
        </p>

        <Link
          href="/"
          className="btn-primary inline-flex items-center gap-2 text-sm mb-10"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Home
        </Link>

        <div className="border-t border-[#262626] pt-8">
          <p className="text-gray-600 text-xs uppercase tracking-wider font-medium mb-4">
            Detection Tools
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/detect/text"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#262626] text-gray-400 hover:text-white hover:border-[#404040] transition-colors text-sm"
            >
              <FileText className="h-3.5 w-3.5" />
              Text
            </Link>
            <Link
              href="/detect/image"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#262626] text-gray-400 hover:text-white hover:border-[#404040] transition-colors text-sm"
            >
              <Image className="h-3.5 w-3.5" />
              Image
            </Link>
            <Link
              href="/detect/audio"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#262626] text-gray-400 hover:text-white hover:border-[#404040] transition-colors text-sm"
            >
              <Mic className="h-3.5 w-3.5" />
              Audio
            </Link>
            <Link
              href="/detect/video"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#262626] text-gray-400 hover:text-white hover:border-[#404040] transition-colors text-sm"
            >
              <Video className="h-3.5 w-3.5" />
              Video
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
