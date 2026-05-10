"use client";

import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";

export default function LandingPage() {
  const router = useRouter();

  const handleStart = () => {
    const token = localStorage.getItem("token");
    if (token) {
      router.push("/analyze");
    } else {
      router.push("/login");
    }
  };

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="text-center max-w-2xl mx-auto space-y-6">
        <div className="inline-flex items-center justify-center p-3 bg-blue-100 text-blue-600 rounded-2xl mb-4">
          <Sparkles className="w-8 h-8" />
        </div>
        <h1 className="text-4xl md:text-6xl font-extrabold text-gray-900 tracking-tight">
          A safe space for your thoughts.
        </h1>
        <p className="text-lg text-gray-500 leading-relaxed max-w-xl mx-auto">
          Our multilingual AI analyzes your text in English or Bengali to help
          you understand your emotional well-being.
        </p>

        <div className="pt-8">
          <button
            onClick={handleStart}
            className="group relative inline-flex items-center justify-center px-8 py-4 text-lg font-semibold text-white bg-blue-600 rounded-full overflow-hidden transition-all hover:bg-blue-700 hover:shadow-xl hover:shadow-blue-200 hover:-translate-y-1"
          >
            Tell us how you are feeling today
          </button>
        </div>
      </div>
    </main>
  );
}
