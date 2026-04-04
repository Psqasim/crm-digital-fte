"""
Phase 2A — Ticket Pattern Analysis Script
NexaFlow Customer Success FTE — GIAIC Hackathon 5

Analyzes 60 sample tickets across email, whatsapp, and web_form channels.
Generates structured report for specs/discovery-log.md.
"""

import json
import os
from collections import defaultdict, Counter
from datetime import datetime

TICKETS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "context", "sample-tickets.json"
)


def load_tickets(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def avg_words(messages: list[str]) -> float:
    if not messages:
        return 0.0
    return round(sum(len(m.split()) for m in messages) / len(messages), 1)


def avg_chars(messages: list[str]) -> float:
    if not messages:
        return 0.0
    return round(sum(len(m) for m in messages) / len(messages), 1)


def detect_edge_cases(tickets: list[dict]) -> list[dict]:
    edge_cases = []
    for t in tickets:
        msg = t["message"]
        reasons = []

        # Non-English (non-ASCII characters dominant or known non-English patterns)
        non_ascii = sum(1 for c in msg if ord(c) > 127)
        if non_ascii > 10:
            reasons.append("non-english")

        # Gibberish / very short / no real words
        words = msg.split()
        alpha_words = [w for w in words if w.isalpha()]
        if len(words) <= 8 and len(alpha_words) < 3:
            reasons.append("gibberish-or-empty")

        # Angry / sentiment negative
        if t.get("sentiment") == "negative":
            reasons.append("angry-negative-sentiment")

        # Refund request
        if any(kw in msg.lower() for kw in ["refund", "charged", "overcharge"]):
            reasons.append("refund-or-billing-dispute")

        # Very long message (> 400 words)
        if len(words) > 400:
            reasons.append("very-long-message")

        # Explicit human request
        if any(kw in msg.lower() for kw in ["speak to a", "talk to a", "manager", "senior engineer", "human"]):
            reasons.append("explicit-human-request")

        # Legal / compliance
        if any(kw in msg.lower() for kw in ["gdpr", "dpa", "legal", "lawsuit", "compliance", "data processing"]):
            reasons.append("legal-compliance")

        # Security incident
        if any(kw in msg.lower() for kw in ["unauthorized", "compromised", "breach", "vietnam", "hacked"]):
            reasons.append("security-incident")

        # Pricing negotiation
        if any(kw in msg.lower() for kw in ["discount", "negotiate", "cheaper", "lower price", "non-profit"]):
            reasons.append("pricing-negotiation")

        if reasons:
            edge_cases.append({
                "id": t["id"],
                "channel": t["channel"],
                "customer_email": t["customer_email"],
                "reasons": reasons,
                "category": t["expected_category"],
                "sentiment": t["sentiment"],
                "message_preview": msg[:80].replace("\n", " ") + ("..." if len(msg) > 80 else ""),
            })
    return edge_cases


def find_cross_channel_customers(tickets: list[dict]) -> dict:
    """Find customers who contacted via multiple channels."""
    email_to_channels = defaultdict(set)
    email_to_ids = defaultdict(list)

    for t in tickets:
        email = t.get("customer_email")
        if email:
            email_to_channels[email].add(t["channel"])
            email_to_ids[email].append(t["id"])

    cross_channel = {
        email: {
            "channels": sorted(channels),
            "ticket_ids": email_to_ids[email],
            "name": next(
                t["customer_name"] for t in tickets if t.get("customer_email") == email
            ),
        }
        for email, channels in email_to_channels.items()
        if len(channels) > 1
    }
    return cross_channel


def analyze_channel(tickets: list[dict], channel: str) -> dict:
    ch_tickets = [t for t in tickets if t["channel"] == channel]
    messages = [t["message"] for t in ch_tickets]
    categories = Counter(t["expected_category"] for t in ch_tickets)
    sentiments = Counter(t["sentiment"] for t in ch_tickets)
    has_phone = sum(1 for t in ch_tickets if t.get("customer_phone"))
    has_email = sum(1 for t in ch_tickets if t.get("customer_email"))

    return {
        "count": len(ch_tickets),
        "avg_words": avg_words(messages),
        "avg_chars": avg_chars(messages),
        "max_words": max((len(m.split()) for m in messages), default=0),
        "min_words": min((len(m.split()) for m in messages), default=0),
        "categories": dict(categories.most_common()),
        "sentiments": dict(sentiments),
        "has_phone_identifier": has_phone,
        "has_email_identifier": has_email,
        "ticket_ids": [t["id"] for t in ch_tickets],
    }


def print_report(tickets: list[dict]) -> None:
    channels = ["email", "whatsapp", "web_form"]
    separator = "=" * 72

    print(separator)
    print("  NEXAFLOW CUSTOMER SUCCESS FTE — TICKET PATTERN ANALYSIS REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(separator)
    print(f"\nTotal tickets analyzed: {len(tickets)}\n")

    # ── Channel summaries ────────────────────────────────────────────────────
    channel_stats = {ch: analyze_channel(tickets, ch) for ch in channels}

    for ch in channels:
        stats = channel_stats[ch]
        print(separator)
        print(f"  CHANNEL: {ch.upper()} ({stats['count']} tickets)")
        print(separator)
        print(f"  Avg message length : {stats['avg_words']} words / {stats['avg_chars']} chars")
        print(f"  Min message length : {stats['min_words']} words")
        print(f"  Max message length : {stats['max_words']} words")
        print(f"  Has email ID       : {stats['has_email_identifier']}/{stats['count']}")
        print(f"  Has phone ID       : {stats['has_phone_identifier']}/{stats['count']}")
        print()
        print("  Categories (ranked):")
        for cat, cnt in sorted(stats["categories"].items(), key=lambda x: -x[1]):
            bar = "█" * cnt
            print(f"    {cat:<22} {cnt:>2}  {bar}")
        print()
        print("  Sentiment distribution:")
        for sent, cnt in sorted(stats["sentiments"].items(), key=lambda x: -x[1]):
            print(f"    {sent:<12} {cnt:>2}")
        print()

    # ── Cross-channel customers ──────────────────────────────────────────────
    print(separator)
    print("  CROSS-CHANNEL CUSTOMERS")
    print(separator)
    cross = find_cross_channel_customers(tickets)
    if cross:
        print(f"  Found {len(cross)} customer(s) who contacted via multiple channels:\n")
        for email, info in cross.items():
            print(f"  Name   : {info['name']}")
            print(f"  Email  : {email}")
            print(f"  Channels: {' + '.join(info['channels'])}")
            print(f"  Tickets : {', '.join(info['ticket_ids'])}")
            print()
    else:
        print("  None found.\n")

    # ── Edge cases ───────────────────────────────────────────────────────────
    print(separator)
    print("  EDGE CASES REQUIRING SPECIAL HANDLING")
    print(separator)
    edge_cases = detect_edge_cases(tickets)
    reason_groups = defaultdict(list)
    for ec in edge_cases:
        for r in ec["reasons"]:
            reason_groups[r].append(ec)

    for reason, cases in sorted(reason_groups.items()):
        print(f"\n  [{reason.upper().replace('-', ' ')}]  ({len(cases)} ticket(s))")
        for ec in cases:
            print(f"    {ec['id']}  [{ec['channel']:<10}]  {ec['customer_email']}")
            print(f"         Preview: {ec['message_preview']}")

    # ── Escalation patterns ──────────────────────────────────────────────────
    print()
    print(separator)
    print("  ESCALATION CATEGORY SUMMARY (expected_category = 'escalation')")
    print(separator)
    escalations = [t for t in tickets if t["expected_category"] == "escalation"]
    print(f"  Total escalation tickets: {len(escalations)}")
    for t in escalations:
        print(f"    {t['id']}  [{t['channel']:<10}]  {t['subject'][:55]}")

    # ── Sentiment summary ────────────────────────────────────────────────────
    print()
    print(separator)
    print("  OVERALL SENTIMENT DISTRIBUTION")
    print(separator)
    all_sentiments = Counter(t["sentiment"] for t in tickets)
    for s, cnt in sorted(all_sentiments.items(), key=lambda x: -x[1]):
        pct = round(cnt / len(tickets) * 100, 1)
        print(f"  {s:<12} {cnt:>3}  ({pct}%)")

    # ── Requirements surfaced ────────────────────────────────────────────────
    print()
    print(separator)
    print("  REQUIREMENTS DISCOVERED FROM TICKET ANALYSIS")
    print(separator)
    requirements = [
        "R1: WhatsApp customers identified by phone (+E.164); must resolve to email for cross-channel unification",
        "R2: Email channel needs thread detection — replies must attach to existing ticket, not open new one",
        "R3: Response length limits enforced: Email ≤500 words, WhatsApp ≤300 chars preferred / 1600 max, Web ≤1000 chars",
        "R4: Non-English messages detected (Urdu TKT-030, Spanish TKT-043); agent must detect language and respond in kind",
        "R5: Gibberish/empty messages (TKT-032) must request clarification rather than create tickets",
        "R6: Cross-channel continuity required: same customer via multiple channels must show unified history",
        "R7: Web form pre-categorizes tickets but category may be wrong (e.g., 'integration' filed as 'feature_question')",
        "R8: Very long messages (TKT-051: ~700 words) need summarization before agent processing to stay within token limits",
        "R9: Enterprise SLA risk: ticket open 3+ hrs must trigger on-call CSM — SLA clock starts on ticket creation timestamp",
        "R10: Multi-ticket context: TKT-046 references TKT-006 (same company); agent must detect same-domain cross-ticket escalation",
        "R11: Pricing negotiation triggers (TKT-020, TKT-040, TKT-055) require immediate escalation, no pricing info revealed",
        "R12: Security incidents (TKT-060) require immediate #security-incidents routing — highest priority escalation type",
    ]
    for r in requirements:
        print(f"  {r}")

    print()
    print(separator)
    print("  END OF REPORT")
    print(separator)


if __name__ == "__main__":
    tickets_path = os.path.abspath(TICKETS_PATH)
    tickets = load_tickets(tickets_path)
    print_report(tickets)
