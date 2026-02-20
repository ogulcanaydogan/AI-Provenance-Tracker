"use client";

import { useState } from "react";
import TextDetector from "@/components/TextDetector";
import ImageDetector from "@/components/ImageDetector";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Link from "next/link";
import {
  FileText,
  Image as ImageIcon,
  Mic,
  Video,
  Shield,
  BarChart3,
  Layers,
  Globe,
  Cpu,
  Eye,
  GitBranch,
  ArrowRight,
} from "lucide-react";

type Tab = "text" | "image";

const CAPABILITIES = [
  {
    icon: Layers,
    title: "Multi-Signal Analysis",
    description:
      "Combines perplexity, burstiness, vocabulary distribution, and ML classifiers into a weighted confidence score — not just a binary yes/no.",
  },
  {
    icon: Eye,
    title: "Explainable Results",
    description:
      "Every detection returns a signal-by-signal breakdown showing exactly why content was flagged, making results transparent and auditable.",
  },
  {
    icon: Shield,
    title: "Multi-Provider Consensus",
    description:
      "Aggregates results from internal detectors and external providers (Copyleaks, Reality Defender, C2PA) with configurable weighting.",
  },
  {
    icon: BarChart3,
    title: "Public Benchmark",
    description:
      "Reproducible evaluation framework with ROC-AUC, calibration ECE, and Brier score across detection, attribution, and tamper robustness tasks.",
  },
  {
    icon: Globe,
    title: "Deploy Anywhere",
    description:
      "Docker Compose for local, Helm charts for Kubernetes, Terraform IaC for AWS — production-ready with API/worker process splitting.",
  },
  {
    icon: GitBranch,
    title: "Open Source",
    description:
      "MIT licensed. Full detection methodology documented. Self-host, audit, and extend with complete transparency.",
  },
];

const MODALITIES = [
  {
    icon: FileText,
    label: "Text",
    href: "/detect/text",
    description: "GPT-4, Claude, Llama detection via perplexity, burstiness, and DistilRoBERTa",
    color: "text-blue-400",
    borderColor: "border-blue-500/20 hover:border-blue-500/40",
  },
  {
    icon: ImageIcon,
    label: "Image",
    href: "/detect/image",
    description: "DALL-E, Midjourney, Stable Diffusion detection via FFT and CNN analysis",
    color: "text-purple-400",
    borderColor: "border-purple-500/20 hover:border-purple-500/40",
  },
  {
    icon: Mic,
    label: "Audio",
    href: "/detect/audio",
    description: "AI speech detection via spectral flatness, dynamic range, and zero-crossing",
    color: "text-emerald-400",
    borderColor: "border-emerald-500/20 hover:border-emerald-500/40",
  },
  {
    icon: Video,
    label: "Video",
    href: "/detect/video",
    description: "Deepfake detection via container signatures and byte-pattern analysis",
    color: "text-orange-400",
    borderColor: "border-orange-500/20 hover:border-orange-500/40",
  },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("text");

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-blue-600/5 via-purple-600/5 to-transparent pointer-events-none" />
          <div className="container mx-auto px-4 pt-16 pb-12 max-w-5xl relative">
            <div className="text-center mb-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5 text-blue-400 text-sm mb-6">
                <Cpu className="h-3.5 w-3.5" />
                <span>Open-source multi-modal AI detection</span>
              </div>
              <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-5 gradient-text leading-tight">
                AI Provenance Tracker
              </h1>
              <p className="text-gray-400 text-lg md:text-xl max-w-3xl mx-auto leading-relaxed">
                Detect AI-generated content across text, images, audio, and video.
                Get explainable confidence scores with full signal breakdowns — not black-box verdicts.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
              <Link
                href="#try-it"
                className="btn-primary inline-flex items-center gap-2 text-sm"
              >
                Try It Now
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="https://github.com/ogulcanaydogan/ai-provenance-tracker"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-[#303030] text-gray-300 hover:text-white hover:border-[#505050] transition-colors text-sm font-medium"
              >
                <GitBranch className="h-4 w-4" />
                View on GitHub
              </Link>
            </div>
          </div>
        </section>

        {/* Modality Cards */}
        <section className="container mx-auto px-4 pb-12 max-w-5xl">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {MODALITIES.map((m) => (
              <Link
                key={m.label}
                href={m.href}
                className={`card p-5 transition-all duration-200 ${m.borderColor} group`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <m.icon className={`h-5 w-5 ${m.color}`} />
                  <span className="font-semibold text-white">{m.label}</span>
                </div>
                <p className="text-gray-500 text-sm leading-relaxed group-hover:text-gray-400 transition-colors">
                  {m.description}
                </p>
              </Link>
            ))}
          </div>
        </section>

        {/* Try It Section */}
        <section id="try-it" className="container mx-auto px-4 py-12 max-w-4xl scroll-mt-8">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">Try It</h2>
            <p className="text-gray-500">
              Paste text or upload an image to see the detection engine in action.
            </p>
          </div>

          <div className="flex justify-center mb-6">
            <div className="inline-flex bg-[#171717] rounded-lg p-1 border border-[#262626]">
              <button
                onClick={() => setActiveTab("text")}
                className={`inline-flex items-center gap-2 px-5 py-2 rounded-md font-medium transition-all text-sm ${
                  activeTab === "text"
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <FileText className="h-4 w-4" />
                Text
              </button>
              <button
                onClick={() => setActiveTab("image")}
                className={`inline-flex items-center gap-2 px-5 py-2 rounded-md font-medium transition-all text-sm ${
                  activeTab === "image"
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <ImageIcon className="h-4 w-4" />
                Image
              </button>
            </div>
          </div>

          <div className="card p-6">
            {activeTab === "text" ? <TextDetector /> : <ImageDetector />}
          </div>
        </section>

        {/* Capabilities Grid */}
        <section className="container mx-auto px-4 py-16 max-w-5xl">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-white mb-2">How It Works</h2>
            <p className="text-gray-500 max-w-2xl mx-auto">
              A multi-signal detection engine that analyses content through multiple independent techniques and combines them into an explainable confidence score.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {CAPABILITIES.map((cap) => (
              <div key={cap.title} className="card p-6 group hover:border-[#363636] transition-colors">
                <cap.icon className="h-5 w-5 text-blue-400 mb-3" />
                <h3 className="font-semibold text-white mb-2">{cap.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">
                  {cap.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Detection Pipeline Visual */}
        <section className="container mx-auto px-4 py-12 max-w-4xl">
          <div className="card p-8 border-[#262626]">
            <h3 className="text-lg font-semibold text-white mb-6 text-center">Detection Pipeline</h3>
            <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-center">
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-blue-400" />
                </div>
                <span className="text-xs text-gray-500 font-medium">Content Input</span>
              </div>

              <ArrowRight className="h-4 w-4 text-gray-600 hidden md:block" />
              <div className="w-px h-6 bg-gray-700 md:hidden" />

              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                  <Cpu className="h-5 w-5 text-purple-400" />
                </div>
                <span className="text-xs text-gray-500 font-medium">Signal Analysis</span>
              </div>

              <ArrowRight className="h-4 w-4 text-gray-600 hidden md:block" />
              <div className="w-px h-6 bg-gray-700 md:hidden" />

              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <Layers className="h-5 w-5 text-emerald-400" />
                </div>
                <span className="text-xs text-gray-500 font-medium">Weighted Aggregation</span>
              </div>

              <ArrowRight className="h-4 w-4 text-gray-600 hidden md:block" />
              <div className="w-px h-6 bg-gray-700 md:hidden" />

              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center">
                  <BarChart3 className="h-5 w-5 text-orange-400" />
                </div>
                <span className="text-xs text-gray-500 font-medium">Confidence Score</span>
              </div>

              <ArrowRight className="h-4 w-4 text-gray-600 hidden md:block" />
              <div className="w-px h-6 bg-gray-700 md:hidden" />

              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                  <Eye className="h-5 w-5 text-red-400" />
                </div>
                <span className="text-xs text-gray-500 font-medium">Explainable Report</span>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="container mx-auto px-4 py-16 max-w-3xl text-center">
          <h2 className="text-2xl font-bold text-white mb-3">Explore the Platform</h2>
          <p className="text-gray-500 mb-8">
            Browse the analytics dashboard, review detection history, or check the API documentation.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[#303030] text-gray-300 hover:text-white hover:border-[#505050] transition-colors text-sm font-medium"
            >
              <BarChart3 className="h-4 w-4" />
              Dashboard
            </Link>
            <Link
              href="/history"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[#303030] text-gray-300 hover:text-white hover:border-[#505050] transition-colors text-sm font-medium"
            >
              <Layers className="h-4 w-4" />
              History
            </Link>
            <Link
              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[#303030] text-gray-300 hover:text-white hover:border-[#505050] transition-colors text-sm font-medium"
            >
              <FileText className="h-4 w-4" />
              API Docs
            </Link>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
