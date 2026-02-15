import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatConfidence(score: number): string {
  return `${score.toFixed(1)}%`;
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString();
}

export function getConfidenceColor(score: number): string {
  if (score < 20) return "#22c55e";      // green
  if (score < 40) return "#86efac";      // light green
  if (score < 60) return "#eab308";      // yellow
  if (score < 80) return "#f97316";      // orange
  return "#ef4444";                       // red
}
