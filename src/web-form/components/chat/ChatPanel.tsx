"use client";

/**
 * components/chat/ChatPanel.tsx
 * Phase 7B: Chat panel — header, messages, typing indicator, input area.
 *
 * Consumes useChatSession hook.
 * Auto-scrolls to latest message via useRef + useEffect.
 * Rate limit: warning banner at 18 messages, locked UI at 20 messages.
 */

import { useEffect, useRef, useState, KeyboardEvent } from "react";
import { ChevronDown, X, Trash2, Send, Bot } from "lucide-react";
import ChatMessage from "./ChatMessage";
import { useChatSession } from "@/hooks/useChatSession";

interface ChatPanelProps {
  onClose: () => void;
  onMinimize: () => void;
}

// Suggestion chips shown on empty state
const SUGGESTIONS = [
  "How do I set up automations?",
  "What integrations are available?",
  "Help with billing",
];

// Typing indicator — three animated dots
function TypingIndicator() {
  return (
    <div className="flex items-start mb-3">
      <div className="bg-slate-700 rounded-2xl rounded-bl-sm px-4 py-3">
        <div className="flex gap-1 items-center">
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function ChatPanel({ onClose, onMinimize }: ChatPanelProps) {
  const { messages, isLoading, warning, isLimitReached, sendMessage, clearChat } =
    useChatSession();

  const [input, setInput] = useState("");
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isLoading || isLimitReached) return;
    setInput("");
    sendMessage(text);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestion = (text: string) => {
    if (!isLoading && !isLimitReached) sendMessage(text);
  };

  const handleClearChat = () => {
    setShowClearConfirm(false);
    clearChat();
  };

  const isOnlyGreeting = messages.length === 1 && messages[0].role === "assistant";
  const canSend = input.trim().length > 0 && !isLoading && !isLimitReached;

  return (
    <div className="flex flex-col h-full">
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                               */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-slate-800 to-slate-900 border-b border-slate-700 rounded-t-2xl flex-shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-semibold text-white">NexaFlow AI Support</span>
          <span className="flex items-center gap-1 text-xs text-emerald-400">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
            Online
          </span>
        </div>
        <div className="flex items-center gap-1">
          {/* Clear chat */}
          {showClearConfirm ? (
            <div className="flex items-center gap-1">
              <button
                onClick={handleClearChat}
                className="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded"
              >
                Clear
              </button>
              <button
                onClick={() => setShowClearConfirm(false)}
                className="text-xs text-slate-400 hover:text-slate-300 px-2 py-1 rounded"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowClearConfirm(true)}
              title="Clear conversation"
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
          {/* Minimize */}
          <button
            onClick={onMinimize}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
          {/* Close */}
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Messages area                                                         */}
      {/* ------------------------------------------------------------------ */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-0 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent"
      >
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {/* Typing indicator */}
        {isLoading && <TypingIndicator />}

        {/* Empty state — shown only when just the greeting is visible */}
        {isOnlyGreeting && !isLoading && (
          <div className="flex flex-col items-center gap-3 mt-4 px-4">
            {/* Bot icon */}
            <div className="w-16 h-16 bg-blue-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center">
              <Bot className="w-9 h-9 text-blue-400" />
            </div>
            {/* Title + subtitle */}
            <div className="text-center">
              <h3 className="text-white font-semibold text-base">NexaFlow AI</h3>
              <p className="text-slate-400 text-sm mt-0.5">
                Intelligent support, powered by AI
              </p>
            </div>
            {/* Suggestion chips */}
            <div className="flex flex-wrap gap-2 justify-center mt-1">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSuggestion(s)}
                  className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-600/60 text-slate-300 hover:text-white px-3 py-1.5 rounded-full transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Rate limit warning banner                                            */}
      {/* ------------------------------------------------------------------ */}
      {warning && !isLimitReached && (
        <div className="mx-4 mb-2 px-3 py-2 bg-amber-900/30 border border-amber-600/50 rounded-lg text-amber-300 text-xs flex-shrink-0">
          ⚠️ {warning}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Input area OR session limit reached                                  */}
      {/* ------------------------------------------------------------------ */}
      {isLimitReached ? (
        <div className="px-4 py-4 border-t border-slate-700 text-center flex-shrink-0">
          <p className="text-slate-400 text-sm mb-2">
            Session limit reached.
          </p>
          <a
            href="/support"
            className="text-blue-400 hover:text-blue-300 text-sm underline"
          >
            Submit a support ticket
          </a>
          {" "}
          <span className="text-slate-500 text-sm">for continued assistance.</span>
        </div>
      ) : (
        <div className="border-t border-slate-700 bg-slate-800 px-3 py-3 flex-shrink-0 rounded-b-2xl">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about NexaFlow..."
              maxLength={500}
              rows={1}
              disabled={isLoading || isLimitReached}
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-400 resize-none outline-none leading-relaxed max-h-24 min-h-[36px] py-2"
              style={{ overflow: "hidden" }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = Math.min(el.scrollHeight, 96) + "px";
              }}
            />
            <button
              onClick={handleSend}
              disabled={!canSend}
              className={`p-2 rounded-lg transition-colors flex-shrink-0 ${
                canSend
                  ? "bg-blue-600 hover:bg-blue-500 text-white"
                  : "bg-slate-700 text-slate-500 cursor-not-allowed"
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          {/* Character counter */}
          {input.length > 400 && (
            <p className="text-xs text-amber-400 mt-1">{input.length}/500</p>
          )}
          {/* Footer */}
          <p className="text-xs text-slate-600 text-center mt-2">
            Powered by NexaFlow AI
          </p>
        </div>
      )}
    </div>
  );
}
