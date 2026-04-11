"use client";

/**
 * components/chat/ChatWidget.tsx
 * Phase 7B (updated): Floating chat button — Bot icon, pulse ring, tooltip.
 *
 * Desktop: 380×520 panel, bottom-right, spring animation.
 * Mobile (<768px): full-screen overlay.
 * Tooltip: "Need help? Ask AI ✨" appears after 3 s, auto-dismisses after 5 s.
 * Pulse ring: CSS ping animation every 3 s while button is visible.
 */

import { useState, useEffect, useCallback } from "react";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { Bot } from "lucide-react";
import ChatPanel from "./ChatPanel";

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [hasUnread, setHasUnread] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  // Detect mobile viewport — client-side only (SSR-safe: default false)
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // Tooltip: show after 3 s, auto-dismiss after 5 s (only when closed)
  useEffect(() => {
    if (isOpen) {
      setShowTooltip(false);
      return;
    }
    const show = setTimeout(() => setShowTooltip(true), 3000);
    return () => clearTimeout(show);
  }, [isOpen]);

  useEffect(() => {
    if (!showTooltip) return;
    const hide = setTimeout(() => setShowTooltip(false), 5000);
    return () => clearTimeout(hide);
  }, [showTooltip]);

  const handleOpen = useCallback(() => {
    setIsOpen(true);
    setIsMinimized(false);
    setHasUnread(false);
    setShowTooltip(false);
  }, []);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    setIsMinimized(false);
  }, []);

  const handleMinimize = useCallback(() => {
    if (isMobile) {
      setIsOpen(false);
    } else {
      setIsMinimized((prev) => !prev);
    }
  }, [isMobile]);

  // Desktop panel animation
  const desktopVariants: Variants = {
    hidden: { y: 20, opacity: 0, scale: 0.97 },
    visible: {
      y: 0,
      opacity: 1,
      scale: 1,
      transition: { type: "spring" as const, stiffness: 350, damping: 28 },
    },
    exit: {
      y: 16,
      opacity: 0,
      scale: 0.97,
      transition: { duration: 0.15 },
    },
  };

  // Mobile overlay animation
  const mobileVariants: Variants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.2 } },
    exit: { opacity: 0, transition: { duration: 0.15 } },
  };

  // Tooltip animation
  const tooltipVariants: Variants = {
    hidden: { opacity: 0, y: 6, scale: 0.95 },
    visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.2 } },
    exit: { opacity: 0, y: 4, scale: 0.95, transition: { duration: 0.15 } },
  };

  return (
    <>
      {/* ------------------------------------------------------------------ */}
      {/* Floating action button + tooltip                                     */}
      {/* ------------------------------------------------------------------ */}
      {(!isOpen || isMobile) && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
          {/* Tooltip bubble */}
          <AnimatePresence>
            {showTooltip && (
              <motion.div
                variants={tooltipVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="bg-slate-800 border border-slate-600 text-white text-sm px-3 py-2 rounded-xl shadow-lg whitespace-nowrap"
              >
                Need help? Ask AI ✨
                {/* Triangle pointer */}
                <span className="absolute -bottom-1.5 right-6 w-3 h-3 bg-slate-800 border-r border-b border-slate-600 rotate-45" />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Button wrapper — relative for pulse ring + badge positioning */}
          <div className="relative">
            {/* Pulse ring — ping animation */}
            {!isOpen && (
              <span className="absolute inset-0 rounded-full bg-blue-500 opacity-30 animate-ping" />
            )}

            <button
              onClick={handleOpen}
              aria-label="Open NexaFlow AI chat"
              className="relative w-[60px] h-[60px] bg-blue-600 hover:bg-blue-500 rounded-full flex items-center justify-center shadow-lg shadow-blue-900/50 transition-colors duration-200"
            >
              <Bot className="w-7 h-7 text-white" />

              {/* Unread badge */}
              {hasUnread && (
                <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 rounded-full border-2 border-[#0F172A]" />
              )}
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Panel (desktop + mobile)                                             */}
      {/* ------------------------------------------------------------------ */}
      <AnimatePresence>
        {isOpen && (
          <>
            {isMobile ? (
              /* Mobile: full-screen overlay */
              <motion.div
                key="mobile-panel"
                variants={mobileVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="fixed inset-0 z-50 bg-[#0F172A] flex flex-col"
              >
                <ChatPanel onClose={handleClose} onMinimize={handleMinimize} />
              </motion.div>
            ) : (
              /* Desktop: 380×520 floating panel */
              <motion.div
                key="desktop-panel"
                variants={desktopVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className={`fixed bottom-24 right-6 z-50 w-[380px] bg-[#0F172A] rounded-2xl shadow-2xl shadow-black/60 border border-slate-700 overflow-hidden flex flex-col transition-[height] duration-200 ${
                  isMinimized ? "h-[52px]" : "h-[520px]"
                }`}
              >
                {isMinimized ? (
                  <div
                    className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-slate-800 to-slate-900 cursor-pointer"
                    onClick={handleMinimize}
                  >
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4 text-blue-400" />
                      <span className="text-sm font-semibold text-white">NexaFlow AI Support</span>
                    </div>
                    <span className="text-slate-400 text-xs">Click to expand</span>
                  </div>
                ) : (
                  <ChatPanel onClose={handleClose} onMinimize={handleMinimize} />
                )}
              </motion.div>
            )}
          </>
        )}
      </AnimatePresence>
    </>
  );
}
