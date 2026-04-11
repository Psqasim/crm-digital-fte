"use client";

/**
 * components/chat/ChatWidget.tsx
 * Phase 7B: Floating chat button + animated panel container.
 *
 * Desktop: 380×520 panel, bottom-right.
 * Mobile (<768px): full-screen overlay.
 * Framer Motion: spring animation on open/close.
 * Unread badge: red dot when closed and messages exist.
 */

import { useState, useEffect } from "react";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { MessageCircle } from "lucide-react";
import ChatPanel from "./ChatPanel";

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [hasUnread, setHasUnread] = useState(false);

  // Detect mobile viewport (client-side only — prevents SSR hydration mismatch)
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const handleOpen = () => {
    setIsOpen(true);
    setIsMinimized(false);
    setHasUnread(false);
  };

  const handleClose = () => {
    setIsOpen(false);
    setIsMinimized(false);
  };

  const handleMinimize = () => {
    if (isMobile) {
      setIsOpen(false);
    } else {
      setIsMinimized((prev) => !prev);
    }
  };

  // Desktop panel animation variants
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

  // Mobile full-screen animation variants
  const mobileVariants: Variants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.2 } },
    exit: { opacity: 0, transition: { duration: 0.15 } },
  };

  return (
    <>
      {/* ------------------------------------------------------------------ */}
      {/* Floating action button                                               */}
      {/* ------------------------------------------------------------------ */}
      {(!isOpen || isMobile) && (
        <button
          onClick={handleOpen}
          aria-label="Open chat"
          className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-blue-600 hover:bg-blue-500 rounded-full flex items-center justify-center shadow-lg shadow-blue-900/40 transition-colors"
        >
          <MessageCircle className="w-6 h-6 text-white" />
          {/* Unread badge */}
          {hasUnread && (
            <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-red-500 rounded-full border-2 border-[#0F172A]" />
          )}
        </button>
      )}

      <AnimatePresence>
        {isOpen && (
          <>
            {/* -------------------------------------------------------------- */}
            {/* Mobile: full-screen overlay                                      */}
            {/* -------------------------------------------------------------- */}
            {isMobile ? (
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
              /* ------------------------------------------------------------ */
              /* Desktop: 380×520 floating panel                                */
              /* ------------------------------------------------------------ */
              <motion.div
                key="desktop-panel"
                variants={desktopVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className={`fixed bottom-24 right-6 z-50 w-[380px] bg-[#0F172A] rounded-2xl shadow-2xl shadow-black/50 border border-slate-700 overflow-hidden flex flex-col transition-all duration-200 ${
                  isMinimized ? "h-[52px]" : "h-[520px]"
                }`}
              >
                {isMinimized ? (
                  // Minimized header only
                  <div
                    className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-slate-800 to-slate-900 cursor-pointer"
                    onClick={handleMinimize}
                  >
                    <span className="text-sm font-semibold text-white">
                      NexaFlow AI Support
                    </span>
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
