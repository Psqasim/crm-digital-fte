-- =============================================================================
-- Migration 002: Seed channel_configs
-- Phase 4A: NexaFlow production channel configuration
-- Limits sourced from context/brand-voice.md and src/agent/channel_formatter.py
-- =============================================================================

INSERT INTO channel_configs (channel, max_response_length, response_style, is_active, config)
VALUES
    (
        'email',
        2500,
        'formal',
        true,
        '{
            "greeting_template": "Dear {name},",
            "signature": "Best regards,\nNexaFlow Support Team\nsupport@nexaflow.io | nexaflow.io",
            "soft_limit": 2000,
            "hard_limit": 2500,
            "tone": "professional",
            "allow_emoji": false,
            "format": "paragraphs"
        }'::jsonb
    ),
    (
        'whatsapp',
        1600,
        'conversational',
        true,
        '{
            "greeting_template": "Hi {name}! \ud83d\udc4b",
            "soft_limit": 300,
            "hard_limit": 1600,
            "max_sentences": 3,
            "tone": "casual",
            "allow_emoji": true,
            "max_emoji_per_message": 1,
            "format": "short"
        }'::jsonb
    ),
    (
        'web_form',
        5000,
        'semi_formal',
        true,
        '{
            "greeting_template": "Hi {name},",
            "soft_limit": 4500,
            "hard_limit": 5000,
            "tone": "semi_formal",
            "allow_emoji": false,
            "format": "structured"
        }'::jsonb
    )
ON CONFLICT (channel) DO UPDATE SET
    max_response_length = EXCLUDED.max_response_length,
    response_style      = EXCLUDED.response_style,
    is_active           = EXCLUDED.is_active,
    config              = EXCLUDED.config;
