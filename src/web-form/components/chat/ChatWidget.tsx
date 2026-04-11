"use client";

/**
 * components/chat/ChatWidget.tsx
 * Phase 7B: Floating chat button + panel container.
 *
 * State (messages, session, loading) lives HERE so it survives:
 *   - minimize/expand toggles
 *   - panel close + reopen (as long as ChatWidget stays mounted)
 * ChatPanel is a pure display component — receives props, no hook of its own.
 */

import { useState, useEffect, useCallback } from "react";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { Bot } from "lucide-react";
import ChatPanel from "./ChatPanel";
import { useChatSession } from "@/hooks/useChatSession";

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  // ── Session state lives here ─────────────────────────────────────────────
  // Kept at ChatWidget level so minimize / close / reopen don't wipe history.
  const { messages, isLoading, warning, isLimitReached, sendMessage, clearChat } =
    useChatSession();

  // ── Viewport detection ───────────────────────────────────────────────────
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // ── Tooltip: show after 3 s, dismiss after 5 s (only when closed) ────────
  useEffect(() => {
    if (isOpen) { setShowTooltip(false); return; }
    const t = setTimeout(() => setShowTooltip(true), 3000);
    return () => clearTimeout(t);
  }, [isOpen]);

  useEffect(() => {
    if (!showTooltip) return;
    const t = setTimeout(() => setShowTooltip(false), 5000);
    return () => clearTimeout(t);
  }, [showTooltip]);

  // ── Handlers ─────────────────────────────────────────────────────────────
  const handleOpen = useCallback(() => {
    setIsOpen(true);
    setIsMinimized(false);
    setShowTooltip(false);
  }, []);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    setIsMinimized(false);
  }, []);

  const handleMinimize = useCallback(() => {
    if (isMobile) setIsOpen(false);
    else setIsMinimized((p) => !p);
  }, [isMobile]);

  // ── Framer Motion variants ────────────────────────────────────────────────
  const desktopVariants: Variants = {
    hidden: { y: 20, opacity: 0, scale: 0.97 },
    visible: {
      y: 0, opacity: 1, scale: 1,
      transition: { type: "spring" as const, stiffness: 350, damping: 28 },
    },
    exit: { y: 16, opacity: 0, scale: 0.97, transition: { duration: 0.15 } },
  };

  const mobileVariants: Variants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.2 } },
    exit: { opacity: 0, transition: { duration: 0.15 } },
  };

  const tooltipVariants: Variants = {
    hidden: { opacity: 0, y: 6, scale: 0.95 },
    visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.2 } },
    exit: { opacity: 0, y: 4, scale: 0.95, transition: { duration: 0.15 } },
  };

  return (
    <>
      {/* ── Floating action button + tooltip ─────────────────────────────── */}
      {(!isOpen || isMobile) && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
          <AnimatePresence>
            {showTooltip && (
              <motion.div
                variants={tooltipVariants}
                initial="hidden" animate="visible" exit="exit"
                className="relative bg-slate-800 border border-slate-600 text-white text-sm px-3 py-2 rounded-xl shadow-lg whitespace-nowrap"
              >
                Need help? Ask AI ✨
                <span className="absolute -bottom-1.5 right-6 w-3 h-3 bg-slate-800 border-r border-b border-slate-600 rotate-45" />
              </motion.div>
            )}
          </AnimatePresence>

          <div className="relative">
            {!isOpen && (
              <span className="absolute inset-0 rounded-full bg-blue-500 opacity-30 animate-ping" />
            )}
            <button
              onClick={handleOpen}
              aria-label="Open NexaFlow AI chat"
              className="relative w-[60px] h-[60px] bg-blue-600 hover:bg-blue-500 rounded-full flex items-center justify-center shadow-lg shadow-blue-900/50 transition-colors duration-200"
            >
              <Bot className="w-7 h-7 text-white" />
              {messages.length > 0 && !isOpen && (
                <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 rounded-full border-2 border-[#0F172A]" />
              )}
            </button>
          </div>
        </div>
      )}

      {/* ── Panel ────────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {isOpen && (
          <>
            {isMobile ? (
              <motion.div
                key="mobile-panel"
                variants={mobileVariants}
                initial="hidden" animate="visible" exit="exit"
                className="fixed inset-0 z-50 bg-[#0F172A] flex flex-col"
              >
                <ChatPanel
                  onClose={handleClose}
                  onMinimize={handleMinimize}
                  messages={messages}
                  isLoading={isLoading}
                  warning={warning}
                  isLimitReached={isLimitReached}
                  onSend={sendMessage}
                  onClear={clearChat}
                />
              </motion.div>
            ) : (
              <motion.div
                key="desktop-panel"
                variants={desktopVariants}
                initial="hidden" animate="visible" exit="exit"
                className={`fixed bottom-24 right-6 z-50 w-[380px] bg-[#0F172A] rounded-2xl shadow-2xl shadow-black/60 border border-slate-700 overflow-hidden flex flex-col transition-[height] duration-200 ${
                  isMinimized ? "h-[52px]" : "h-[520px]"
                }`}
              >
                {/* Minimized bar */}
                {isMinimized && (
                  <div
                    className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-slate-800 to-slate-900 cursor-pointer flex-shrink-0"
                    onClick={handleMinimize}
                  >
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4 text-blue-400" />
                      <span className="text-sm font-semibold text-white">NexaFlow AI Support</span>
                    </div>
                    <span className="text-slate-400 text-xs">Click to expand</span>
                  </div>
                )}
                {/* ChatPanel — always mounted; hidden via CSS when minimized */}
                <div
                  className="flex flex-col flex-1 min-h-0"
                  style={{ display: isMinimized ? "none" : undefined }}
                >
                  <ChatPanel
                    onClose={handleClose}
                    onMinimize={handleMinimize}
                    messages={messages}
                    isLoading={isLoading}
                    warning={warning}
                    isLimitReached={isLimitReached}
                    onSend={sendMessage}
                    onClear={clearChat}
                  />
                </div>
              </motion.div>
            )}
          </>
        )}
      </AnimatePresence>
    </>
  );
}
