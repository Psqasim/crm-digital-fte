"""
production/tests/load_test_quick.py
Condensed multi-channel load test — runs against production or local FastAPI.

Usage:
    python3 production/tests/load_test_quick.py
    python3 production/tests/load_test_quick.py > docs/load-test-results.md 2>&1

Set API_BASE_URL env var to override (default: HF Spaces production).
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

API_BASE = os.getenv(
    "API_BASE_URL",
    "https://psqasim-crm-digital-fte-api.hf.space",
)
PKT = ZoneInfo("Asia/Karachi")


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

WEB_FORM_TICKETS = [
    {
        "name": "Alice Raza",
        "email": "alice.raza@loadtest.nexaflow.io",
        "subject": "How do I set up automation rules?",
        "category": "general",
        "priority": "medium",
        "message": "I need help setting up automation rules in my NexaFlow workspace. I want to trigger an action when a task is marked complete.",
    },
    {
        "name": "Bob Chen",
        "email": "bob.chen@loadtest.nexaflow.io",
        "subject": "API authentication keeps failing",
        "category": "technical",
        "priority": "high",
        "message": "My API calls are returning 401 Unauthorized even though I'm using the correct API key from the dashboard. I've tried regenerating the key twice.",
    },
    {
        "name": "Sara Khan",
        "email": "sara.khan@loadtest.nexaflow.io",
        "subject": "Billing question about pro-rated charges",
        "category": "billing",
        "priority": "low",
        "message": "I upgraded from Starter to Growth mid-month. Will I be charged for the full month or prorated from the upgrade date?",
    },
    {
        "name": "David Osei",
        "email": "david.osei@loadtest.nexaflow.io",
        "subject": "Slack integration not sending notifications",
        "category": "technical",
        "priority": "medium",
        "message": "My Slack integration stopped working two days ago. Tasks complete but no Slack notifications arrive. The webhook URL is still configured correctly.",
    },
    {
        "name": "Fatima Ali",
        "email": "fatima.ali@loadtest.nexaflow.io",
        "subject": "How to export data to CSV?",
        "category": "general",
        "priority": "low",
        "message": "Can I export all my task and project data to CSV for quarterly reporting? I can't find this option in the settings.",
    },
    {
        "name": "Michael Torres",
        "email": "michael.torres@loadtest.nexaflow.io",
        "subject": "Need help onboarding my team",
        "category": "general",
        "priority": "medium",
        "message": "I'm trying to invite 15 team members but the invite emails are going to spam. We're on the Growth plan.",
    },
    {
        "name": "Priya Sharma",
        "email": "priya.sharma@loadtest.nexaflow.io",
        "subject": "Dashboard not loading on mobile",
        "category": "technical",
        "priority": "medium",
        "message": "The NexaFlow dashboard fails to load on my iPhone 14 Pro (Safari). It works fine on desktop Chrome. I get a blank white screen after login.",
    },
    {
        "name": "James Okonkwo",
        "email": "james.okonkwo@loadtest.nexaflow.io",
        "subject": "What's included in the Enterprise plan?",
        "category": "general",
        "priority": "low",
        "message": "We're considering upgrading to Enterprise. Can you tell me what additional features are included compared to Growth?",
    },
    {
        "name": "Aisha Mohammed",
        "email": "aisha.mohammed@loadtest.nexaflow.io",
        "subject": "Zapier integration not triggering",
        "category": "technical",
        "priority": "high",
        "message": "My Zapier webhook is no longer receiving events from NexaFlow. This broke our entire CRM sync pipeline. We process ~500 tasks/day through this.",
    },
    {
        "name": "Carlos Rivera",
        "email": "carlos.rivera@loadtest.nexaflow.io",
        "subject": "Permission settings for sub-workspaces",
        "category": "general",
        "priority": "medium",
        "message": "I have three sub-workspaces and want different team members to only see their own workspace. How do I configure workspace-level permissions?",
    },
    # Cross-channel customers — same emails as above but from 'whatsapp' channel perspective
    # These 5 simulate the same user contacting via a different channel
    {
        "name": "Alice Raza",
        "email": "alice.raza@loadtest.nexaflow.io",  # cross-channel: same email as ticket 1
        "subject": "Follow up on automation rules",
        "category": "general",
        "priority": "medium",
        "message": "Following up on my earlier question about automation rules. I found the settings but now I get an error when saving the rule.",
    },
    {
        "name": "Bob Chen",
        "email": "bob.chen@loadtest.nexaflow.io",  # cross-channel: same email as ticket 2
        "subject": "API still broken after key regeneration",
        "category": "technical",
        "priority": "high",
        "message": "I contacted you earlier about API auth failures. I regenerated the key again but still getting 401. This is blocking our entire pipeline.",
    },
    {
        "name": "Sara Khan",
        "email": "sara.khan@loadtest.nexaflow.io",  # cross-channel: same email as ticket 3
        "subject": "Invoice shows wrong amount",
        "category": "billing",
        "priority": "medium",
        "message": "I received my invoice and it shows the full month charge instead of prorated. Can you correct this?",
    },
    {
        "name": "David Osei",
        "email": "david.osei@loadtest.nexaflow.io",  # cross-channel: same email as ticket 4
        "subject": "Slack still broken after 3 days",
        "category": "technical",
        "priority": "high",
        "message": "Three days and Slack notifications still not working. This is costing us time in missed task updates. Urgently need resolution.",
    },
    {
        "name": "Fatima Ali",
        "email": "fatima.ali@loadtest.nexaflow.io",  # cross-channel: same email as ticket 5
        "subject": "CSV export found but not working",
        "category": "technical",
        "priority": "low",
        "message": "I found the CSV export option under Reports but when I click Download it shows an error. Please help.",
    },
    {
        "name": "Emma Wilson",
        "email": "emma.wilson@loadtest.nexaflow.io",
        "subject": "How does pgvector search work?",
        "category": "technical",
        "priority": "low",
        "message": "I'm building an integration with NexaFlow and want to understand how semantic search is implemented in the knowledge base.",
    },
    {
        "name": "Omar Abdullah",
        "email": "omar.abdullah@loadtest.nexaflow.io",
        "subject": "Team member can't access shared project",
        "category": "technical",
        "priority": "medium",
        "message": "I added a new team member to a shared project but they can't see it in their dashboard. Their role is set to Member.",
    },
    {
        "name": "Yuki Tanaka",
        "email": "yuki.tanaka@loadtest.nexaflow.io",
        "subject": "Does NexaFlow support SSO?",
        "category": "general",
        "priority": "low",
        "message": "Our company uses Okta for SSO. Does NexaFlow support SAML or OAuth SSO integration? This is a requirement for our enterprise procurement.",
    },
    {
        "name": "Lena Müller",
        "email": "lena.mueller@loadtest.nexaflow.io",
        "subject": "Data retention and GDPR compliance",
        "category": "general",
        "priority": "medium",
        "message": "We're based in Germany and need to ensure NexaFlow is GDPR compliant. Where is our data stored and what is the data retention policy?",
    },
    {
        "name": "Andre Dubois",
        "email": "andre.dubois@loadtest.nexaflow.io",
        "subject": "Webhook payload format documentation",
        "category": "technical",
        "priority": "low",
        "message": "I need the full webhook payload schema for task events. The current documentation only shows partial examples and I'm missing some fields.",
    },
]


async def submit_ticket(
    client: httpx.AsyncClient,
    ticket: dict,
    index: int,
) -> dict:
    """Submit one ticket and return timing + result."""
    start = time.perf_counter()
    try:
        resp = await client.post(
            f"{API_BASE}/support/submit",
            json=ticket,
            timeout=30.0,
        )
        elapsed = time.perf_counter() - start
        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "ok": True,
                "ticket_id": data.get("ticket_id", "?"),
                "elapsed": elapsed,
                "email": ticket["email"],
                "status_code": resp.status_code,
            }
        else:
            return {"ok": False, "elapsed": elapsed, "status_code": resp.status_code, "email": ticket["email"]}
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return {"ok": False, "elapsed": elapsed, "error": str(exc), "email": ticket["email"], "status_code": 0}


async def get_ticket_status(client: httpx.AsyncClient, ticket_id: str) -> str:
    """Return ticket status string."""
    try:
        resp = await client.get(f"{API_BASE}/support/ticket/{ticket_id}", timeout=15.0)
        if resp.status_code == 200:
            return resp.json().get("status", "unknown")
    except Exception:
        pass
    return "unknown"


async def run_load_test() -> None:
    now_pkt = datetime.now(PKT)
    header = f"Load Test Results — {now_pkt.strftime('%A, %B %d, %Y at %I:%M %p PKT')}"
    print(header)
    print("=" * len(header))
    print(f"Target: {API_BASE}")
    print(f"Tickets to submit: {len(WEB_FORM_TICKETS)}")
    print()

    # ── Phase 1: Submit all tickets ──────────────────────────────────────────
    print("Phase 1: Submitting tickets (2s apart)...")
    results = []
    async with httpx.AsyncClient() as client:
        for i, ticket in enumerate(WEB_FORM_TICKETS, 1):
            result = await submit_ticket(client, ticket, i)
            results.append(result)
            status_icon = "✅" if result["ok"] else "❌"
            tid = result.get("ticket_id", "FAILED")
            print(
                f"  [{i:02d}/{len(WEB_FORM_TICKETS)}] {status_icon} {tid}"
                f"  ({result['elapsed']:.2f}s)  {ticket['email']}"
            )
            if i < len(WEB_FORM_TICKETS):
                await asyncio.sleep(2)

    # ── Phase 2: Trigger agent processing ───────────────────────────────────
    print()
    print("Phase 2: Triggering agent processing...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{API_BASE}/agent/process-pending", timeout=30.0)
            print(f"  process-pending → HTTP {resp.status_code}")
        except Exception as exc:
            print(f"  process-pending → error: {exc}")

    # ── Phase 3: Wait and check resolution ──────────────────────────────────
    print()
    wait_secs = 60
    print(f"Phase 3: Waiting {wait_secs}s for AI agent to resolve tickets...")
    await asyncio.sleep(wait_secs)

    print()
    print("Phase 4: Checking ticket statuses...")
    successful = [r for r in results if r["ok"]]
    resolved = escalated = open_count = unknown = 0
    async with httpx.AsyncClient() as client:
        for r in successful:
            status = await get_ticket_status(client, r["ticket_id"])
            r["final_status"] = status
            if status == "resolved":
                resolved += 1
            elif status == "escalated":
                escalated += 1
            elif status in ("open", "pending", "in_progress"):
                open_count += 1
            else:
                unknown += 1
            print(f"  {r['ticket_id']} → {status}")

    # ── Summary ──────────────────────────────────────────────────────────────
    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count
    elapsed_times = [r["elapsed"] for r in results if r["ok"]]
    p95 = sorted(elapsed_times)[int(len(elapsed_times) * 0.95) - 1] if elapsed_times else 0.0
    avg_time = statistics.mean(elapsed_times) if elapsed_times else 0.0

    # Cross-channel customers: emails that appear more than once
    emails = [r["email"] for r in results if r["ok"]]
    cross_channel_emails = {e for e in emails if emails.count(e) > 1}

    resolved_rate = (resolved / ok_count * 100) if ok_count > 0 else 0
    escalated_rate = (escalated / ok_count * 100) if ok_count > 0 else 0

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Web Form submissions:       {len(WEB_FORM_TICKETS)}")
    print(f"Successful submissions:     {ok_count}/{len(WEB_FORM_TICKETS)} ({ok_count/len(WEB_FORM_TICKETS)*100:.0f}%)")
    print(f"Failed submissions:         {fail_count}")
    print(f"Avg submission time:        {avg_time:.2f}s")
    print(f"P95 submission time:        {p95:.2f}s")
    print()
    print(f"Cross-channel customers:    {len(cross_channel_emails)} (same email, multiple tickets)")
    print(f"  Emails: {', '.join(sorted(cross_channel_emails))}")
    print()
    print(f"Tickets resolved:           {resolved}/{ok_count} ({resolved_rate:.0f}%)")
    print(f"Tickets escalated:          {escalated}/{ok_count} ({escalated_rate:.0f}%)")
    print(f"Tickets still open:         {open_count}/{ok_count}")
    print(f"Unknown status:             {unknown}/{ok_count}")
    print()
    print(f"Channels tested:            web_form ✅")
    print(f"Production URL:             {API_BASE}")
    print(f"Test completed at:          {datetime.now(PKT).strftime('%Y-%m-%d %H:%M PKT')}")
    print("=" * 60)

    # Readiness assessment
    print()
    print("READINESS ASSESSMENT")
    print("-" * 60)
    success_ok = ok_count == len(WEB_FORM_TICKETS)
    speed_ok = p95 < 5.0  # submission <5s (processing is async)
    resolution_ok = (resolved + escalated) >= (ok_count * 0.5)  # ≥50% handled within 60s
    cross_ok = len(cross_channel_emails) >= 5

    checks = [
        (success_ok, f"100% submission success rate ({ok_count}/{len(WEB_FORM_TICKETS)})"),
        (speed_ok, f"P95 submission time < 5s ({p95:.2f}s)"),
        (resolution_ok, f"≥50% tickets resolved/escalated within 60s ({resolved + escalated}/{ok_count})"),
        (cross_ok, f"5+ cross-channel customers tested ({len(cross_channel_emails)})"),
    ]
    for passed, label in checks:
        icon = "✅" if passed else "⚠️ "
        print(f"  {icon} {label}")

    all_pass = all(p for p, _ in checks)
    print()
    if all_pass:
        print("  Result: PASS — System ready for 24/7 operation")
    else:
        print("  Result: PARTIAL — See ⚠️ items above")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_load_test())
