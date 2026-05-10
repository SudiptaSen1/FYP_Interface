"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Loader2,
  ThumbsUp,
  ThumbsDown,
  Send,
  CheckCircle,
  Bot,
} from "lucide-react";

type AnalysisResult = {
  detected_language: string;
  prediction: string;
  confidence: number;
};

export default function AnalyzePage() {
  const router = useRouter();

  // --- Route Protection ---
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login"); // Kick unauthorized users back to login
    }
  }, [router]);

  // --- State Management ---
  const [statement, setStatement] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");

  const [feedbackState, setFeedbackState] = useState<
    "idle" | "correcting" | "submitted"
  >("idle");
  const [correction, setCorrection] = useState("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  // --- API Handlers ---
  const handleAnalyze = async () => {
    if (!statement.trim()) return;

    setIsLoading(true);
    setError("");
    setResult(null);
    setFeedbackState("idle");
    setCorrection("");

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ statement }),
        },
      );

      if (!response.ok) throw new Error("Failed to analyze text");

      const data: AnalysisResult = await response.json();
      setResult(data);
    } catch (err) {
      setError("An error occurred while connecting to the server.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeedback = async (type: "upvote" | "downvote") => {
    if (!result) return;

    // Show input box when downvote is clicked
    if (type === "downvote" && feedbackState !== "correcting") {
      setFeedbackState("correcting");
      return;
    }

    setIsSubmittingFeedback(true);
    try {
      const payload = {
        statement,
        language: result.detected_language,
        original_prediction: result.prediction,
        feedback_type: type,
        // Send the correction if they typed one, otherwise send null
        corrected_prediction:
          type === "downvote" && correction.trim() ? correction.trim() : null,
      };

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/feedback`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );

      if (!response.ok) throw new Error("Failed to submit feedback");
      setFeedbackState("submitted");
    } catch (err) {
      setError("Failed to submit feedback.");
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  // --- Render UI ---
  return (
    <main className="min-h-[calc(100vh-4rem)] bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl p-6 md:p-8 border border-gray-100 mt-8 mb-8">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-800">
            MindFlow Analyzer
          </h1>
          <p className="text-gray-500 text-sm mt-2">
            Write your thoughts in English or Bengali.
          </p>
        </div>

        {/* Input Area */}
        <div className="space-y-4">
          <textarea
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            placeholder="Type your statement here..."
            className="w-full h-32 p-4 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none transition-all text-gray-700"
          />

          <button
            onClick={handleAnalyze}
            disabled={isLoading || !statement.trim()}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
            {isLoading ? "Analyzing..." : "Analyze Text"}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
            {error}
          </div>
        )}

        {/* Results Area */}
        {result && (
          <div className="mt-8 pt-8 border-t border-gray-100 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
              Results
            </h2>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                <span className="text-xs text-gray-500 block mb-1">
                  Language
                </span>
                <span className="font-medium text-gray-800">
                  {result.detected_language}
                </span>
              </div>
              <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                <span className="text-xs text-gray-500 block mb-1">
                  Confidence
                </span>
                <span className="font-medium text-gray-800">
                  {(result.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="bg-blue-50/50 p-6 rounded-xl border border-blue-100 text-center mb-6">
              <span className="text-sm text-blue-600/80 font-medium block mb-2">
                Prediction
              </span>
              <span className="text-2xl font-bold text-blue-900">
                {result.prediction}
              </span>
            </div>

            {/* --- MINDFLOW CHAT TRIGGER (UPDATED FIX) --- */}
            {result.prediction.toLowerCase() !== "normal" && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-xl border border-indigo-100 text-center mb-6 animate-in fade-in zoom-in duration-500">
                <h3 className="text-lg font-semibold text-indigo-900 mb-2">
                  You don't have to face this alone.
                </h3>
                <p className="text-sm text-indigo-700/80 mb-4">
                  MindFlow is a safe, AI-powered space where you can talk about
                  how you're feeling right now.
                </p>
                <button
                  // --- CHANGE IS HERE: Pass the prediction as a URL parameter ---
                  onClick={() =>
                    router.push(
                      `/chat?prediction=${encodeURIComponent(result.prediction)}`,
                    )
                  }
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 px-6 rounded-full transition-all shadow-md hover:shadow-lg flex items-center gap-2 mx-auto"
                >
                  <Bot className="w-4 h-4" />
                  Talk to MindFlow
                </button>
              </div>
            )}

            {/* --- FEEDBACK SECTION --- */}
            <div className="border-t border-gray-100 pt-6">
              {feedbackState === "submitted" ? (
                <div className="flex items-center justify-center gap-2 text-green-600 bg-green-50 p-3 rounded-xl">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-medium text-sm">
                    Thank you for your feedback!
                  </span>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <span className="text-sm text-gray-600">
                      Is this prediction accurate?
                    </span>
                    <div className="flex gap-2 w-full sm:w-auto">
                      <button
                        onClick={() => handleFeedback("upvote")}
                        disabled={
                          isSubmittingFeedback || feedbackState === "correcting"
                        }
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-gray-50 hover:bg-green-50 text-gray-600 hover:text-green-600 rounded-lg border border-gray-200 hover:border-green-200 transition-colors"
                      >
                        <ThumbsUp className="w-4 h-4" /> Yes
                      </button>
                      <button
                        onClick={() => handleFeedback("downvote")}
                        disabled={isSubmittingFeedback}
                        className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                          feedbackState === "correcting"
                            ? "bg-red-50 text-red-600 border-red-200"
                            : "bg-gray-50 hover:bg-red-50 text-gray-600 hover:text-red-600 border-gray-200 hover:border-red-200"
                        }`}
                      >
                        <ThumbsDown className="w-4 h-4" /> No
                      </button>
                    </div>
                  </div>

                  {/* Correction Input (Shows only if Downvoted) */}
                  {feedbackState === "correcting" && (
                    <div className="animate-in fade-in slide-in-from-top-2 duration-300 flex gap-2">
                      <input
                        type="text"
                        value={correction}
                        onChange={(e) => setCorrection(e.target.value)}
                        placeholder={`Optional: What should the prediction be?`}
                        className="flex-1 px-4 py-2 rounded-lg border border-gray-200 focus:ring-2 focus:ring-red-500 outline-none text-sm"
                      />
                      <button
                        onClick={() => handleFeedback("downvote")}
                        disabled={isSubmittingFeedback}
                        className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isSubmittingFeedback ? "Submitting..." : "Submit"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
