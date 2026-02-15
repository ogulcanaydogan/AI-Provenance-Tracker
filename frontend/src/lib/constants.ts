export const SAMPLE_AI_TEXT = `The integration of artificial intelligence into modern healthcare systems represents a paradigm shift in how medical professionals approach patient care and diagnosis. Machine learning algorithms have demonstrated remarkable accuracy in analyzing medical imaging, often matching or exceeding the performance of experienced radiologists. These systems process vast datasets of patient information to identify patterns that might escape human observation, enabling earlier detection of conditions ranging from cancer to cardiovascular disease. Furthermore, AI-powered predictive models are transforming preventive medicine by assessing individual risk factors and recommending personalized intervention strategies. The continuous improvement of these technologies, coupled with increasing computational capabilities, suggests that AI will play an increasingly central role in shaping the future of healthcare delivery worldwide.`;

export const VERDICT_LABELS: Record<string, string> = {
  human: "Human Written",
  likely_human: "Likely Human",
  uncertain: "Uncertain",
  likely_ai: "Likely AI",
  ai_generated: "AI Generated",
};

export const VERDICT_COLORS: Record<string, string> = {
  human: "text-green-400",
  likely_human: "text-green-300",
  uncertain: "text-yellow-400",
  likely_ai: "text-orange-400",
  ai_generated: "text-red-400",
};

export const VERDICT_BG_COLORS: Record<string, string> = {
  human: "bg-green-500/10 border-green-500/20",
  likely_human: "bg-green-500/10 border-green-500/20",
  uncertain: "bg-yellow-500/10 border-yellow-500/20",
  likely_ai: "bg-orange-500/10 border-orange-500/20",
  ai_generated: "bg-red-500/10 border-red-500/20",
};
