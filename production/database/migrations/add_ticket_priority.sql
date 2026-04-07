-- Migration: add_ticket_priority
-- Phase 4C-iii: Add priority column to tickets table (backwards-compatible)
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'medium';
