"use client";

/**
 * components/chat/ChatMessage.tsx
 * Phase 7B (updated): Individual message bubble with markdown rendering.
 *
 * Renders common markdown patterns without an external library:
 * ### heading, **bold**, - bullets, numbered lists, line breaks.
 * Uses dangerouslySetInnerHTML — input is AI-generated, not user input.
 */

import type { ChatMessage as ChatMessageType } from "@/hooks/useChatSession";

interface ChatMessageProps {
  message: ChatMessageType;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * Convert AI markdown response to safe HTML for display in chat bubbles.
 * Handles: headings (###/##/#), **bold**, *italic*, - bullets, numbered lists,
 * blank-line paragraphs, and newlines.
 */
function markdownToHtml(text: string): string {
  const lines = text.split("\n");
  const output: string[] = [];
  let inList = false;

  const closeList = () => {
    if (inList) {
      output.push("</ul>");
      inList = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Escape HTML entities first (security — AI text only, but belt-and-suspenders)
    line = line
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Inline: **bold**
    line = line.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    // Inline: *italic*
    line = line.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Headings ###
    if (/^###\s+(.+)/.test(line)) {
      closeList();
      output.push(`<p class="font-semibold text-slate-100 mt-2 mb-0.5">${line.replace(/^###\s+/, "")}</p>`);
      continue;
    }
    if (/^##\s+(.+)/.test(line)) {
      closeList();
      output.push(`<p class="font-bold text-slate-100 mt-2 mb-0.5">${line.replace(/^##\s+/, "")}</p>`);
      continue;
    }
    if (/^#\s+(.+)/.test(line)) {
      closeList();
      output.push(`<p class="font-bold text-slate-100 mt-2 mb-1">${line.replace(/^#\s+/, "")}</p>`);
      continue;
    }

    // Unordered list: - item
    if (/^[-*]\s+(.+)/.test(line)) {
      if (!inList) {
        output.push('<ul class="list-disc list-inside space-y-0.5 my-1 pl-1">');
        inList = true;
      }
      output.push(`<li class="text-sm leading-relaxed">${line.replace(/^[-*]\s+/, "")}</li>`);
      continue;
    }

    // Numbered list: 1. item
    if (/^\d+\.\s+(.+)/.test(line)) {
      if (!inList) {
        output.push('<ul class="list-decimal list-inside space-y-0.5 my-1 pl-1">');
        inList = true;
      }
      output.push(`<li class="text-sm leading-relaxed">${line.replace(/^\d+\.\s+/, "")}</li>`);
      continue;
    }

    closeList();

    // Blank line → spacing
    if (line.trim() === "") {
      output.push('<div class="h-1" />');
      continue;
    }

    // Regular paragraph line
    output.push(`<p class="leading-relaxed">${line}</p>`);
  }

  closeList();
  return output.join("");
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col mb-3 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[85%] px-4 py-2.5 text-sm ${
          isUser
            ? "bg-blue-600 text-white rounded-2xl rounded-br-sm"
            : "bg-slate-700 text-slate-100 rounded-2xl rounded-bl-sm"
        }`}
      >
        {isUser ? (
          // User messages: plain text (no markdown needed)
          <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          // AI messages: render markdown
          <div
            className="prose-chat"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(message.content) }}
          />
        )}
      </div>
      <span className="text-xs text-slate-500 mt-1 px-1">
        {formatTime(message.timestamp)}
      </span>
    </div>
  );
}
