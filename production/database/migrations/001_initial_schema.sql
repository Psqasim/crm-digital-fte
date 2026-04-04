-- =============================================================================
-- NexaFlow CRM Digital FTE Factory — Production Schema
-- Phase 4A: Neon PostgreSQL 16 + pgvector
-- Context7 verified: vector(1536) + ivfflat cosine index syntax
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- customers
-- Unified customer record; email is the primary identity key
-- =============================================================================
CREATE TABLE IF NOT EXISTS customers (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    name        VARCHAR(255),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    metadata    JSONB        NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_customers_email
    ON customers (email);

-- =============================================================================
-- customer_identifiers
-- Maps phone numbers / WhatsApp IDs to a customer record
-- =============================================================================
CREATE TABLE IF NOT EXISTS customer_identifiers (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id      UUID         NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type  VARCHAR(50)  NOT NULL,   -- 'phone', 'whatsapp_id', etc.
    identifier_value VARCHAR(255) NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (identifier_type, identifier_value)
);

CREATE INDEX IF NOT EXISTS idx_customer_identifiers_lookup
    ON customer_identifiers (identifier_type, identifier_value);

-- =============================================================================
-- conversations
-- One session per customer per channel
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID        NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel     VARCHAR(50) NOT NULL,   -- 'email', 'whatsapp', 'web_form'
    status      VARCHAR(50) NOT NULL DEFAULT 'open',  -- open/pending/escalated/resolved
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata    JSONB       NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_conversations_customer_id
    ON conversations (customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_channel
    ON conversations (channel);
CREATE INDEX IF NOT EXISTS idx_conversations_status
    ON conversations (status);

-- =============================================================================
-- messages
-- Every message in every conversation (customer + agent turns)
-- =============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,   -- 'customer' or 'agent'
    content         TEXT        NOT NULL,
    channel         VARCHAR(50) NOT NULL,
    sentiment_score FLOAT,                 -- -1.0 to 1.0; NULL if not evaluated
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB       NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at
    ON messages (created_at);

-- =============================================================================
-- tickets
-- Support ticket linked to a conversation
-- =============================================================================
CREATE TABLE IF NOT EXISTS tickets (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID         NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id         UUID         NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel             VARCHAR(50)  NOT NULL,
    subject             VARCHAR(500),
    category            VARCHAR(100),  -- billing/feature_question/bug/onboarding/integration/escalation
    priority            VARCHAR(20)   NOT NULL DEFAULT 'normal',  -- low/normal/high/urgent
    status              VARCHAR(50)   NOT NULL DEFAULT 'open',
    escalation_reason   TEXT,
    resolution_summary  TEXT,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tickets_customer_id
    ON tickets (customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status
    ON tickets (status);
CREATE INDEX IF NOT EXISTS idx_tickets_channel
    ON tickets (channel);
CREATE INDEX IF NOT EXISTS idx_tickets_category
    ON tickets (category);

-- =============================================================================
-- knowledge_base
-- Product documentation chunks with pgvector embeddings
-- Embedding: OpenAI text-embedding-3-small — 1536 dimensions
-- =============================================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    title      VARCHAR(500) NOT NULL,
    content    TEXT         NOT NULL,
    category   VARCHAR(100),
    embedding  vector(1536),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    metadata   JSONB        NOT NULL DEFAULT '{}'
);

-- ivfflat cosine index — Context7/pgvector verified syntax
-- lists=100 appropriate for up to ~100k rows
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding
    ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================================================
-- channel_configs
-- Per-channel runtime settings
-- =============================================================================
CREATE TABLE IF NOT EXISTS channel_configs (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    channel             VARCHAR(50)  UNIQUE NOT NULL,
    max_response_length INT,
    response_style      VARCHAR(100),
    is_active           BOOLEAN      NOT NULL DEFAULT true,
    config              JSONB        NOT NULL DEFAULT '{}'
);

-- =============================================================================
-- agent_metrics
-- Operational monitoring data (consumed by Phase 4G metrics collector)
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_metrics (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name  VARCHAR(100) NOT NULL,
    metric_value FLOAT        NOT NULL,
    channel      VARCHAR(50),
    recorded_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    metadata     JSONB        NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_agent_metrics_metric_name
    ON agent_metrics (metric_name);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_recorded_at
    ON agent_metrics (recorded_at);
