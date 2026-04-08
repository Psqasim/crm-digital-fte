"""
production/workers/metrics_collector.py
Phase 4G: Background metrics collection job.

Runs every 5 minutes, counts ticket states, and records data points
to agent_metrics via queries.record_metric().
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

COLLECTION_INTERVAL_SECONDS = 300  # 5 minutes


async def collect_once() -> None:
    """Run a single metrics collection cycle."""
    from production.database.queries import get_db_pool, record_metric

    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT "
                "  COUNT(*) AS total, "
                "  COUNT(*) FILTER (WHERE status = 'open') AS open_count, "
                "  COUNT(*) FILTER (WHERE status = 'resolved') AS resolved_count, "
                "  COUNT(*) FILTER (WHERE status = 'escalated') AS escalated_count "
                "FROM tickets"
            )
            total = int(row["total"])
            open_count = int(row["open_count"])
            resolved_count = int(row["resolved_count"])
            escalated_count = int(row["escalated_count"])
            escalation_rate = round((escalated_count / total) * 100, 1) if total > 0 else 0.0

            channel_rows = await conn.fetch(
                "SELECT channel, COUNT(*) AS cnt FROM tickets GROUP BY channel"
            )
            channel_counts: dict[str, int] = {
                r["channel"]: int(r["cnt"]) for r in channel_rows
            }

        # Record global metrics
        await record_metric(pool, "tickets.open.count", float(open_count))
        await record_metric(pool, "tickets.resolved.count", float(resolved_count))
        await record_metric(pool, "tickets.escalated.count", float(escalated_count))
        await record_metric(pool, "escalation_rate", escalation_rate)

        # Record per-channel metrics
        for ch in ("email", "whatsapp", "web_form"):
            count = float(channel_counts.get(ch, 0))
            await record_metric(pool, f"channel.{ch}.count", count, channel=ch)

        logger.info(
            "[metrics_collector] recorded — open=%d resolved=%d escalated=%d "
            "escalation_rate=%.1f%% channels=%s",
            open_count,
            resolved_count,
            escalated_count,
            escalation_rate,
            channel_counts,
        )
    except Exception:
        logger.exception("[metrics_collector] collection cycle failed")


async def run_forever() -> None:
    """Loop forever, collecting metrics every COLLECTION_INTERVAL_SECONDS."""
    logger.info(
        "[metrics_collector] starting — interval=%ds", COLLECTION_INTERVAL_SECONDS
    )
    while True:
        await collect_once()
        await asyncio.sleep(COLLECTION_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    asyncio.run(run_forever())
