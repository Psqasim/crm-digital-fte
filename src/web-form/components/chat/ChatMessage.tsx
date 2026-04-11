"use client";

/**
 * components/chat/ChatMessage.tsx
 * Phase 7B: Individual message bubble with markdown rendering.
 *
 * AI messages: rendered via markdownToHtml — handles headings, bold, italic,
 * bullets, numbered lists, inline code, fenced code blocks, line breaks.
 * User messages: plain text with whitespace-pre-wrap (preserves line breaks).
 *
 * Long message safety: break-words applied to bubble so URLs/long strings
 * never overflow the panel.
 */

import type { ChatMessage as ChatMessageType } from "@/hooks/useChatSession";

interface ChatMessageProps {
  message: ChatMessageType;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * Convert AI markdown to safe HTML for display in chat bubbles.
 *
 * Processing order (applied per-line unless noted):
 *   1. Fenced code blocks (```…```) — multi-line, extracted first
 *   2. HTML entity escaping (security)
 *   3. Inline: **bold**, *italic*, `code`
 *   4. Headings: ###, ##, #
 *   5. Unordered lists: - item / * item
 *   6. Ordered lists: 1. item
 *   7. Blank lines → small spacer
 *   8. Regular paragraph
 */
function markdownToHtml(text: string): string {
  // ── Step 1: extract fenced code blocks before line splitting ─────────────
  const CODE_BLOCK_PLACEHOLDER = "\x00CODE\x00";
  const codeBlocks: string[] = [];

  const withoutFenced = text.replace(/```[\w]*\n?([\s\S]*?)```/g, (_match, code: string) => {
    const escaped = code
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    codeBlocks.push(
      `<pre class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 my-2 overflow-x-auto text-xs text-slate-200 whitespace-pre-wrap break-all"><code>${escaped.trim()}</code></pre>`
    );
    return CODE_BLOCK_PLACEHOLDER;
  });

  // ── Step 2–8: process line by line ───────────────────────────────────────
  const lines = withoutFenced.split("\n");
  const output: string[] = [];
  let inUl = false;
  let inOl = false;

  const closeUl = () => { if (inUl) { output.push("</ul>"); inUl = false; } };
  const closeOl = () => { if (inOl) { output.push("</ol>"); inOl = false; } };
  const closeLists = () => { closeUl(); closeOl(); };

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Restore fenced code block placeholders
    if (line.trim() === CODE_BLOCK_PLACEHOLDER) {
      closeLists();
      output.push(codeBlocks.shift()!);
      continue;
    }

    // HTML entity escaping (security — belt-and-suspenders even for AI output)
    line = line
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Inline `code`
    line = line.replace(/`([^`]+)`/g, '<code class="bg-slate-900 border border-slate-700 rounded px-1 py-0.5 text-xs text-blue-300 font-mono">$1</code>');

    // Inline **bold**
    line = line.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    // Inline *italic*
    line = line.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Headings
    if (/^###\s+/.test(line)) {
      closeLists();
      output.push(`<p class="font-semibold text-slate-100 mt-2 mb-0.5">${line.replace(/^###\s+/, "")}</p>`);
      continue;
    }
    if (/^##\s+/.test(line)) {
      closeLists();
      output.push(`<p class="font-bold text-slate-100 mt-2 mb-0.5">${line.replace(/^##\s+/, "")}</p>`);
      continue;
    }
    if (/^#\s+/.test(line)) {
      closeLists();
      output.push(`<p class="font-bold text-slate-100 mt-2 mb-1">${line.replace(/^#\s+/, "")}</p>`);
      continue;
    }

    // Unordered list: - item  or  * item
    if (/^[-*]\s+/.test(line)) {
      closeOl();
      if (!inUl) { output.push('<ul class="list-disc list-inside space-y-0.5 my-1 pl-1">'); inUl = true; }
      output.push(`<li class="text-sm leading-relaxed">${line.replace(/^[-*]\s+/, "")}</li>`);
      continue;
    }

    // Ordered list: 1. item
    if (/^\d+\.\s+/.test(line)) {
      closeUl();
      if (!inOl) { output.push('<ol class="list-decimal list-inside space-y-0.5 my-1 pl-1">'); inOl = true; }
      output.push(`<li class="text-sm leading-relaxed">${line.replace(/^\d+\.\s+/, "")}</li>`);
      continue;
    }

    closeLists();

    // Blank line → small spacer
    if (line.trim() === "") {
      output.push('<div class="h-1" />');
      continue;
    }

    // Regular paragraph
    output.push(`<p class="leading-relaxed">${line}</p>`);
  }

  closeLists();
  return output.join("");
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col mb-3 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[85%] px-4 py-2.5 text-sm break-words ${
          isUser
            ? "bg-blue-600 text-white rounded-2xl rounded-br-sm"
            : "bg-slate-700 text-slate-100 rounded-2xl rounded-bl-sm"
        }`}
      >
        {isUser ? (
          <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
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
