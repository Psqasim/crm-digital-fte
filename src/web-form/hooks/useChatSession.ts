"use client";

/**
 * hooks/useChatSession.ts
 * Phase 7B: State machine for the NexaFlow chat widget.
 *
 * Manages: session lifecycle, message history, loading state, rate limit UI.
 * Calls the Next.js proxy at /api/chat which forwards to FastAPI /chat/message.
 */

import { useState, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatSessionState {
  sessionId: string;
  messages: ChatMessage[];
  isLoading: boolean;
  messageCount: number;
  warning: string | null;
  isLimitReached: boolean;
}

// ---------------------------------------------------------------------------
// Greeting constant
// ---------------------------------------------------------------------------

function makeGreeting(): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "Hi! I'm NexaFlow's AI assistant. How can I help you today?",
    timestamp: new Date(),
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useChatSession() {
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([makeGreeting()]);
  const [isLoading, setIsLoading] = useState(false);
  const [messageCount, setMessageCount] = useState(0);
  const [warning, setWarning] = useState<string | null>(null);
  const [isLimitReached, setIsLimitReached] = useState(false);

  // -------------------------------------------------------------------------
  // sendMessage — core function (HIGH RISK: concurrent guard + finally block)
  // -------------------------------------------------------------------------

  const sendMessage = useCallback(
    async (text: string) => {
      // Guard: block concurrent sends
      if (isLoading || isLimitReached || !text.trim()) return;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
      };

      // Append user message immediately (optimistic)
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        // Build history: last 10 messages BEFORE this new message
        // (we use setMessages callback below, so snapshot current messages)
        const history = messages
          .slice(-10)
          .map((m) => ({ role: m.role, content: m.content }));

        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text.trim(),
            session_id: sessionId,
            history,
          }),
        });

        if (!res.ok) {
          // Non-200: surface a user-friendly error bubble
          const errorMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: "assistant",
            content:
              "I'm having trouble connecting. Please try again or use our support form.",
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errorMsg]);
          return;
        }

        const data = await res.json();

        const aiMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.reply,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, aiMsg]);
        setSessionId(data.session_id ?? "");
        setWarning(data.warning ?? null);

        const newCount = messageCount + 1;
        setMessageCount(newCount);
        if (newCount >= 20) setIsLimitReached(true);
      } catch {
        // Network error
        const errorMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            "I'm having trouble connecting. Please try again or use our support form.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        // Always restore loading state — HIGH RISK: must be in finally
        setIsLoading(false);
      }
    },
    [isLoading, isLimitReached, messages, messageCount, sessionId]
  );

  // -------------------------------------------------------------------------
  // clearChat — reset all state (HIGH RISK: sessionId must reset to "")
  // -------------------------------------------------------------------------

  const clearChat = useCallback(() => {
    setMessages([makeGreeting()]);
    setSessionId(""); // "" signals fresh session to backend
    setMessageCount(0);
    setWarning(null);
    setIsLimitReached(false);
  }, []);

  return {
    messages,
    sessionId,
    isLoading,
    warning,
    isLimitReached,
    sendMessage,
    clearChat,
  };
}
