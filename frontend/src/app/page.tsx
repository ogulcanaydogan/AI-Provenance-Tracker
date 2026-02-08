"use client";

import { useState } from "react";
import TextDetector from "@/components/TextDetector";
import ImageDetector from "@/components/ImageDetector";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

type Tab = "text" | "image";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("text");

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 container mx-auto px-4 py-8 max-w-4xl">
        {/* Hero Section */}
        <section className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 gradient-text">
            AI Provenance Tracker
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Detect AI-generated content with confidence. Analyze text and images
            to verify authenticity using advanced detection algorithms.
          </p>
        </section>

        {/* Tab Navigation */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex bg-[#171717] rounded-lg p-1 border border-[#262626]">
            <button
              onClick={() => setActiveTab("text")}
              className={`px-6 py-2 rounded-md font-medium transition-all ${
                activeTab === "text"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Text Detection
            </button>
            <button
              onClick={() => setActiveTab("image")}
              className={`px-6 py-2 rounded-md font-medium transition-all ${
                activeTab === "image"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Image Detection
            </button>
          </div>
        </div>

        {/* Detector Components */}
        <div className="card p-6">
          {activeTab === "text" ? <TextDetector /> : <ImageDetector />}
        </div>

        {/* Features Section */}
        <section className="mt-16 grid md:grid-cols-3 gap-6">
          <div className="card p-6 text-center">
            <div className="text-3xl mb-3">🔍</div>
            <h3 className="font-semibold mb-2">Multi-Signal Analysis</h3>
            <p className="text-gray-400 text-sm">
              Combines perplexity, burstiness, and pattern analysis for accurate detection
            </p>
          </div>
          <div className="card p-6 text-center">
            <div className="text-3xl mb-3">📊</div>
            <h3 className="font-semibold mb-2">Detailed Reports</h3>
            <p className="text-gray-400 text-sm">
              Get confidence scores and explanations for every analysis
            </p>
          </div>
          <div className="card p-6 text-center">
            <div className="text-3xl mb-3">🔒</div>
            <h3 className="font-semibold mb-2">Privacy First</h3>
            <p className="text-gray-400 text-sm">
              Your content is analyzed and never stored or shared
            </p>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
