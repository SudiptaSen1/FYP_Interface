"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Send, Loader2, Bot, User, ArrowLeft, ShieldAlert } from "lucide-react";

type ChatMessage = {
  role: "user" | "model";
  content: string;
};

export default function ChatPage() {
  const router = useRouter();

  // Route Protection
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) router.push("/login");
  }, [router]);

  // State Management
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Auto-scroll reference
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Read URL parameter and set dynamic greeting
  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const prediction = searchParams.get("prediction");

    let greeting =
      "Hi there. I'm MindFlow. I'm here to listen, support you, and help you navigate how you are feeling. What's on your mind today?";

    if (prediction) {
      const condition = prediction.toLowerCase();

      // Customize the intro based on the severity of the model's result
      if (condition === "suicidal") {
        greeting =
          "Hi there. I'm MindFlow. Your analysis indicated you might be experiencing suicidal thoughts. Please know that your life has value, and you don't have to carry this heavy burden alone. I am here to listen to whatever is on your mind without judgment.";
      } else if (condition === "depression") {
        greeting =
          "Hi there. I'm MindFlow. I understand your text analysis showed signs of depression. It takes a lot of courage to reach out. I'm here to offer a safe space to talk. How are you feeling right now?";
      } else if (condition === "anxiety") {
        greeting =
          "Hi there. I'm MindFlow. I see your analysis indicated signs of anxiety. It is completely okay to feel overwhelmed sometimes. I'm here to help you unpack those feelings. What is causing you stress today?";
      } else {
        greeting = `Hi there. I'm MindFlow. I understand your analysis indicated signs of ${condition}. I'm a safe, supportive space to talk about it. What's on your mind today?`;
      }
    }

    setMessages([{ role: "model", content: greeting }]);
  }, []);

  const handleSendMessage = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput(""); // Clear input box immediately

    // 1. Add user message to UI immediately
    const updatedHistory = [...messages];
    setMessages([...updatedHistory, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      // 2. Send request to backend (Current message + past history)
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          history: updatedHistory,
        }),
      });

      if (!response.ok) throw new Error("Failed to connect to MindFlow.");

      const data = await response.json();

      // 3. Add AI response to UI
      setMessages((prev) => [...prev, { role: "model", content: data.reply }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "model",
          content:
            "I'm having a little trouble connecting right now. Please try again in a moment.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-gray-50 flex items-center justify-center p-4 md:p-6">
      <div className="w-full max-w-3xl bg-white rounded-2xl shadow-xl flex flex-col h-[80vh] border border-gray-100 overflow-hidden">
        {/* Chat Header */}
        <div className="bg-white border-b border-gray-100 p-4 flex items-center justify-between z-10 shadow-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/analyze")}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h2 className="font-bold text-gray-800 flex items-center gap-2">
                MindFlow Support <Bot className="w-5 h-5 text-blue-600" />
              </h2>
              <p className="text-xs text-green-600 font-medium flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block"></span>{" "}
                Online
              </p>
            </div>
          </div>

          <div className="flex items-center text-xs text-gray-400 bg-gray-50 px-3 py-1.5 rounded-full border border-gray-100 gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5" />
            AI Assistant (Not a doctor)
          </div>
        </div>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 bg-gray-50/50">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex items-start gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 flex-shrink-0 rounded-full flex items-center justify-center ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 text-gray-600"
                }`}
              >
                {msg.role === "user" ? (
                  <User className="w-5 h-5" />
                ) : (
                  <Bot className="w-5 h-5" />
                )}
              </div>

              {/* Message Bubble */}
              <div
                className={`max-w-[75%] md:max-w-[65%] rounded-2xl px-5 py-3.5 text-sm md:text-base leading-relaxed ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-tr-sm shadow-md shadow-blue-200"
                    : "bg-white text-gray-700 border border-gray-100 rounded-tl-sm shadow-sm"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {/* Invisible div to scroll to */}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white border-t border-gray-100">
          <form
            onSubmit={handleSendMessage}
            className="flex items-end gap-2 max-w-4xl mx-auto relative"
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Type your message..."
              className="w-full max-h-32 min-h-[52px] resize-none bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 pr-14 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-700"
              rows={1}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim() || messages.length === 0}
              className="absolute right-2 bottom-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center h-9 w-9"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4 ml-0.5" />
              )}
            </button>
          </form>
          <p className="text-center text-[10px] text-gray-400 mt-2">
            MindFlow can make mistakes. Consider verifying critical medical
            information with a professional.
          </p>
        </div>
      </div>
    </main>
  );
}
