"use client";

/**
 * components/chat/ChatMessage.tsx
 * Phase 7B: Individual message bubble for the chat widget.
 *
 * User: right-aligned, blue bubble
 * Assistant: left-aligned, slate bubble
 */

import type { ChatMessage as ChatMessageType } from "@/hooks/useChatSession";

interface ChatMessageProps {
  message: ChatMessageType;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col mb-3 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[80%] px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white rounded-2xl rounded-br-sm"
            : "bg-slate-700 text-slate-100 rounded-2xl rounded-bl-sm"
        }`}
      >
        {message.content}
      </div>
      <span className="text-xs text-slate-500 mt-1 px-1">
        {formatTime(message.timestamp)}
      </span>
    </div>
  );
}
