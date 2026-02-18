import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Provenance Tracker — Detect AI-Generated Content",
  description:
    "Open-source platform to detect AI-generated text, images, audio, and video. Get explainable confidence scores with full signal breakdowns.",
  keywords: [
    "AI detection",
    "deepfake detection",
    "AI-generated content",
    "content authenticity",
    "GPT detector",
    "AI provenance",
    "text detection",
    "image detection",
  ],
  authors: [{ name: "Ogulcan Aydogan", url: "https://ogulcanaydogan.com" }],
  metadataBase: new URL("https://github.com/ogulcanaydogan/AI-Provenance-Tracker"),
  openGraph: {
    title: "AI Provenance Tracker",
    description:
      "Detect AI-generated content across text, images, audio, and video with explainable scoring and multi-provider consensus.",
    type: "website",
    siteName: "AI Provenance Tracker",
    locale: "en_GB",
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Provenance Tracker",
    description:
      "Open-source multi-modal AI content detection with explainable scoring.",
    creator: "@ogulcanaydogan",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} antialiased`}>{children}</body>
    </html>
  );
}
