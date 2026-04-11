"use client";

/**
 * components/chat/ChatPanel.tsx
 * Phase 7B (updated): Chat panel — cleaner UI, no duplicate greeting.
 *
 * Empty state: shows Bot icon + subtitle + suggestion chips (no bubble).
 * Once user sends first message, chat bubbles appear normally.
 * "New Chat" button replaces the Trash + confirm flow.
 */

import { useEffect, useRef, useState, KeyboardEvent } from "react";
import { ChevronDown, X, Send, Bot, Plus, RotateCcw } from "lucide-react";
import ChatMessage from "./ChatMessage";
import { useChatSession } from "@/hooks/useChatSession";

interface ChatPanelProps {
  onClose: () => void;
  onMinimize: () => void;
}

const SUGGESTIONS = [
  "How do I set up automations?",
  "What integrations are available?",
  "Help with billing",
];

function TypingIndicator() {
  return (
    <div className="flex items-start mb-3">
      <div className="w-7 h-7 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center flex-shrink-0 mr-2 mt-0.5">
        <Bot className="w-3.5 h-3.5 text-blue-400" />
      </div>
      <div className="bg-slate-800 border border-slate-700 rounded-2xl rounded-bl-sm px-4 py-3">
        <div className="flex gap-1 items-center">
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"
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
  const scrollRef = useRef<HTMLDivElement>(null);

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

  // isOnlyGreeting: only the auto-greeting exists, user hasn't typed yet
  const isOnlyGreeting = messages.length === 1 && messages[0].role === "assistant";
  const canSend = input.trim().length > 0 && !isLoading && !isLimitReached;
  const hasConversation = messages.length > 1;

  return (
    <div className="flex flex-col h-full bg-[#0F172A]">

      {/* ------------------------------------------------------------------ */}
      {/* Header                                                               */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/60 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white leading-none">NexaFlow AI</p>
            <p className="text-xs text-emerald-400 mt-0.5 flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full inline-block" />
              Online · AI Support
            </p>
          </div>
        </div>

        <div className="flex items-center gap-0.5">
          {/* New Chat — only show when there's a conversation */}
          {hasConversation && (
            <button
              onClick={clearChat}
              title="New conversation"
              className="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onMinimize}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 rounded-lg transition-colors"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Content area                                                          */}
      {/* ------------------------------------------------------------------ */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-4"
      >
        {/* Empty state — shown INSTEAD of the greeting bubble */}
        {isOnlyGreeting && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center pb-4">
            <div className="w-16 h-16 rounded-2xl bg-blue-600/15 border border-blue-500/25 flex items-center justify-center">
              <Bot className="w-8 h-8 text-blue-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-base">NexaFlow AI Support</h3>
              <p className="text-slate-400 text-sm mt-1 leading-relaxed">
                Ask me anything about NexaFlow —<br />integrations, billing, automations, or troubleshooting.
              </p>
            </div>
            <div className="flex flex-col gap-2 w-full mt-1">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSuggestion(s)}
                  className="w-full text-left text-sm bg-slate-800/60 hover:bg-slate-700/80 border border-slate-700/60 hover:border-slate-600 text-slate-300 hover:text-white px-4 py-2.5 rounded-xl transition-colors flex items-center gap-2"
                >
                  <Plus className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Conversation — only render message bubbles once user has started chatting */}
        {hasConversation && (
          <>
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
          </>
        )}

        {/* Loading state on first message (no prior messages to show) */}
        {isOnlyGreeting && isLoading && <TypingIndicator />}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Rate limit warning                                                   */}
      {/* ------------------------------------------------------------------ */}
      {warning && !isLimitReached && (
        <div className="mx-4 mb-2 px-3 py-2 bg-amber-900/20 border border-amber-600/30 rounded-lg text-amber-300 text-xs flex-shrink-0">
          ⚠️ {warning}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Input area                                                            */}
      {/* ------------------------------------------------------------------ */}
      {isLimitReached ? (
        <div className="px-4 py-4 border-t border-slate-700/60 text-center flex-shrink-0">
          <p className="text-slate-400 text-sm mb-3">Session limit reached.</p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={clearChat}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              New Chat
            </button>
            <a
              href="/support"
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm rounded-lg transition-colors"
            >
              Support Form
            </a>
          </div>
        </div>
      ) : (
        <div className="border-t border-slate-700/60 px-3 py-3 flex-shrink-0">
          <div className="flex items-end gap-2 bg-slate-800/60 rounded-xl border border-slate-700/60 px-3 py-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about NexaFlow..."
              maxLength={500}
              rows={1}
              disabled={isLoading || isLimitReached}
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 resize-none outline-none leading-relaxed max-h-24 min-h-[28px] py-1"
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
              className={`p-1.5 rounded-lg transition-colors flex-shrink-0 ${
                canSend
                  ? "bg-blue-600 hover:bg-blue-500 text-white"
                  : "text-slate-600 cursor-not-allowed"
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          {input.length > 400 && (
            <p className="text-xs text-amber-400 mt-1.5 px-1">{input.length}/500</p>
          )}
          <p className="text-xs text-slate-700 text-center mt-2">
            Powered by NexaFlow AI
          </p>
        </div>
      )}
    </div>
  );
}
