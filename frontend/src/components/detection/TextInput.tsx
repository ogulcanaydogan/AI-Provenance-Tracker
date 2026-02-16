"use client";

import { useState } from "react";
import { SAMPLE_AI_TEXT } from "@/lib/constants";
import { ClipboardPaste, Trash2, FlaskConical } from "lucide-react";

interface TextInputProps {
  onAnalyze: (text: string) => void;
  isLoading: boolean;
}

export function TextInput({ onAnalyze, isLoading }: TextInputProps) {
  const [text, setText] = useState("");
  const maxLength = 50000;

  async function handlePaste() {
    try {
      const clipboard = await navigator.clipboard.readText();
      setText(clipboard);
    } catch {
      // Clipboard API may not be available
    }
  }

  return (
    <div className="space-y-4">
      <div className="relative">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste or type text to analyze (minimum 50 characters)..."
          className="w-full h-64 bg-gray-900 border border-gray-700 rounded-xl p-4 text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-colors text-sm leading-relaxed"
          maxLength={maxLength}
          disabled={isLoading}
        />
        <div className="absolute bottom-3 right-3 text-xs text-gray-500">
          {text.length.toLocaleString()} / {maxLength.toLocaleString()}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => onAnalyze(text)}
          disabled={text.length < 50 || isLoading}
          className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-medium rounded-xl hover:from-blue-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-sm"
        >
          {isLoading ? "Analyzing..." : "Analyze Text"}
        </button>

        <button
          onClick={handlePaste}
          disabled={isLoading}
          className="px-4 py-2.5 bg-gray-800 text-gray-300 rounded-xl hover:bg-gray-700 transition-colors text-sm flex items-center gap-2"
        >
          <ClipboardPaste className="h-4 w-4" />
          Paste
        </button>

        <button
          onClick={() => setText(SAMPLE_AI_TEXT)}
          disabled={isLoading}
          className="px-4 py-2.5 text-gray-400 hover:text-gray-200 transition-colors text-sm flex items-center gap-2"
        >
          <FlaskConical className="h-4 w-4" />
          Try Sample
        </button>

        {text.length > 0 && (
          <button
            onClick={() => setText("")}
            disabled={isLoading}
            className="px-4 py-2.5 text-gray-500 hover:text-gray-300 transition-colors text-sm flex items-center gap-2 ml-auto"
          >
            <Trash2 className="h-4 w-4" />
            Clear
          </button>
        )}
      </div>
    </div>
  );
}
