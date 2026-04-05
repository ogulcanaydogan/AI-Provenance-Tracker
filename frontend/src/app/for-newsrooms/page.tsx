"use client";

import Link from "next/link";
import { CheckCircle2, Shield, Gauge, FileJson } from "lucide-react";

const PLANS = [
  {
    name: "Starter",
    price: "$149/mo",
    target: "Small fact-check desks",
    limits: ["20k requests/month", "120 req/min burst", "Shared support SLA"],
  },
  {
    name: "Pro",
    price: "$599/mo",
    target: "Regional newsroom teams",
    limits: ["120k requests/month", "300 req/min burst", "Priority support + onboarding"],
  },
  {
    name: "Enterprise",
    price: "Custom",
    target: "National / network organizations",
    limits: ["1M+ requests/month", "Custom burst/SLA", "Dedicated security + deployment support"],
  },
];

export default function NewsroomPricingPage() {
  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
      <section className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-sm text-blue-300">
          <Shield className="h-4 w-4" />
          Fact-check workflow API
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-white">
          Newsroom API Plans
        </h1>
        <p className="text-gray-400 max-w-3xl">
          Evidence-first AI provenance detection for editorial verification pipelines.
          Conservative false-positive profile, explainable results, API key quota control,
          and Instagram mention triage for social verification desks.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/detect/url"
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
          >
            Try URL Analysis
          </Link>
          <Link
            href="https://api.whoisfake.com/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg border border-[#333] text-gray-200 hover:text-white hover:border-[#4a4a4a] text-sm transition-colors"
          >
            Open API Docs
          </Link>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PLANS.map((plan) => (
          <article
            key={plan.name}
            className="rounded-2xl border border-[#2a2a2a] bg-[#121212] p-6 space-y-4"
          >
            <div>
              <h2 className="text-xl font-semibold text-white">{plan.name}</h2>
              <p className="text-blue-300 text-lg mt-1">{plan.price}</p>
              <p className="text-sm text-gray-500 mt-1">{plan.target}</p>
            </div>
            <ul className="space-y-2">
              {plan.limits.map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-gray-300">
                  <CheckCircle2 className="h-4 w-4 mt-0.5 text-emerald-400" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      <section className="rounded-2xl border border-[#262626] bg-[#111] p-6 space-y-4">
        <div className="flex items-center gap-2 text-gray-200">
          <FileJson className="h-4 w-4 text-blue-400" />
          <h2 className="text-lg font-semibold">Evidence Payload (sample)</h2>
        </div>
        <pre className="overflow-x-auto rounded-xl bg-black/40 border border-[#2f2f2f] p-4 text-xs text-gray-200">
{`{
  "analysis_id": "8ec9b7f1-...",
  "content_type": "text",
  "verdict": "uncertain",
  "confidence": 0.57,
  "timestamp": "2026-03-19T13:00:00Z",
  "source_url": "https://example.com/article",
  "detector_versions": {
    "model_version": "text-detector:distilroberta-v1",
    "calibration_version": "calibrated-20260312:news"
  }
}`}
        </pre>
      </section>

      <section className="rounded-2xl border border-[#262626] bg-[#111] p-6 space-y-3">
        <h2 className="text-lg font-semibold text-white">Social Verification Desk</h2>
        <p className="text-sm text-gray-400">
          Tag <span className="text-blue-300 font-medium">@whoisfake</span> or DM a public
          Instagram link to trigger automated intake. Owned-media comments can receive a public
          reply; third-party mentions fall back to DM plus an evidence link.
        </p>
        <p className="text-sm text-gray-500">
          This keeps the public workflow visible while preserving deterministic behavior for
          private or no-public-media posts.
        </p>
      </section>

      <section className="rounded-2xl border border-[#262626] bg-[#111] p-6">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Gauge className="h-4 w-4 text-amber-400" />
          SLA and Reliability
        </h2>
        <p className="text-sm text-gray-400 mt-2">
          Production deploy uses pinned images, post-deploy smoke gate, and evidence-locked benchmark checks.
          Contact for custom latency/SLA terms and private deployment requirements.
        </p>
      </section>
    </main>
  );
}
