"use client";

/**
 * components/chat/ChatWidgetPortal.tsx
 * Phase 7B: Thin client wrapper for layout insertion.
 *
 * Route-group approach: this component is imported by (main)/layout.tsx which
 * already excludes /login (handled by (auth) route group). The usePathname check
 * below is a belt-and-suspenders guard for any edge cases.
 */

import { usePathname } from "next/navigation";
import { ChatWidget } from "./ChatWidget";

export default function ChatWidgetPortal() {
  const pathname = usePathname();

  // Hide on login page — (main) route group handles this at layout level,
  // but guard here too for edge cases (direct navigation, etc.)
  if (pathname === "/login") return null;

  return <ChatWidget />;
}
