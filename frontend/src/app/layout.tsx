import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Provenance Tracker - Detect AI-Generated Content",
  description: "Detect AI-generated text and images. Verify content authenticity with confidence scores and detailed analysis.",
  keywords: ["AI detection", "deepfake", "AI-generated content", "authenticity", "GPT detector"],
  authors: [{ name: "Ogulcan Aydogan" }],
  openGraph: {
    title: "AI Provenance Tracker",
    description: "Detect AI-generated content, trace origins, verify authenticity",
    type: "website",
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
