# Edge Cases Test Dataset

60 test tickets from `context/sample-tickets.json` — 20 per channel.
Each documents the edge case type, expected agent behavior, and whether a test exists.

---

## Email Channel (TKT-001 to TKT-020)

| Ticket ID | Edge Case Type | Expected Behavior | Test Exists |
|-----------|---------------|-------------------|-------------|
| TKT-001 | Integration failure — OAuth expired | Guide re-auth via Settings → Integrations → Slack → Reconnect | `test_agent_tools.py` |
| TKT-002 | Feature how-to — multi-step automation setup | Step-by-step guide: Automations → New Rule → configure trigger + action | `test_agent_tools.py` |
| TKT-003 | Billing — plan upgrade inquiry | Explain Growth plan pricing, link to billing page | `test_agent_tools.py` |
| TKT-004 | Bug — third-party sync failure (Google Calendar) | Troubleshoot: reconnect integration, check calendar permissions | `test_database.py` |
| TKT-005 | Feature question — permissions & roles | Explain Admin/Member/Viewer roles; how to assign | `test_agent_tools.py` |
| TKT-006 | Angry customer + implicit cancellation threat | Negative sentiment detected → escalate immediately; empathetic opener | `test_e2e.py::test_escalation_path` |
| TKT-007 | Refund request | Escalate — refund outside agent scope; 1 business day SLA | `test_e2e.py::test_escalation_path` |
| TKT-008 | New user onboarding — first-time setup | Guided onboarding steps; positive tone | `test_agent_tools.py` |
| TKT-009 | Integration bug — GitHub not creating issues | Check webhook config; re-authorize GitHub app | `test_agent_tools.py` |
| TKT-010 | Feature question — data export | Explain CSV export: Settings → Data → Export | `test_agent_tools.py` |
| TKT-011 | Subscription cancellation | Confirm cancellation steps; offer retention if applicable; escalate if billing | `test_agent_tools.py` |
| TKT-012 | Bug — webhook timeouts | Suggest retry config, timeout increase; escalate if recurring | `test_database.py` |
| TKT-013 | Bug — mobile app display issue | Check app version; suggest update; escalate if up to date | `test_agent_tools.py` |
| TKT-014 | Enterprise plan inquiry (positive sentiment) | Explain Enterprise features; escalate to sales | `test_agent_tools.py` |
| TKT-015 | Bug — duplicate tickets from Jira sync | Deduplication fix instructions; check Jira webhook settings | `test_agent_tools.py` |
| TKT-016 | Bug — role change not propagating | Ask to wait 5 min + refresh; if persists → escalate | `test_agent_tools.py` |
| TKT-017 | Feature question — Microsoft Teams integration | Confirm Teams integration availability; link to docs | `test_agent_tools.py` |
| TKT-018 | Enterprise API rate limit request | Escalate to sales for Enterprise rate limit increase | `test_agent_tools.py` |
| TKT-019 | Positive feedback + onboarding question | Acknowledge praise; answer team onboarding question | `test_agent_tools.py` |
| TKT-020 | Pricing negotiation / discount request | Escalate to sales — outside agent authority | `test_agent_tools.py` |

---

## WhatsApp Channel (TKT-021 to TKT-040)

| Ticket ID | Edge Case Type | Expected Behavior | Test Exists |
|-----------|---------------|-------------------|-------------|
| TKT-021 | Integration error — short WhatsApp message | Detect integration issue from brief message; ask for details | `test_whatsapp_handler.py` |
| TKT-022 | Onboarding — "how to add team members" | Short step guide: Settings → Team → Invite | `test_whatsapp_handler.py` |
| TKT-023 | App crash — negative sentiment | Empathetic response; escalate data loss risk | `test_whatsapp_handler.py` |
| TKT-024 | Mobile app availability question | Confirm iOS/Android app availability | `test_whatsapp_handler.py` |
| TKT-025 | Bug — automation stopped working | Basic troubleshoot: check rule status, re-enable | `test_whatsapp_handler.py` |
| TKT-026 | Wrong charge — negative billing | Apologize; escalate to billing team immediately | `test_whatsapp_handler.py` |
| TKT-027 | Short feature question — data export via WhatsApp | Brief answer with steps | `test_whatsapp_handler.py` |
| TKT-028 | Auth bug — can't login post password reset | Clear cookies; try incognito; escalate if stuck | `test_whatsapp_handler.py` |
| TKT-029 | Feature question — task priorities | Explain priority setting: task card → Priority dropdown | `test_whatsapp_handler.py` |
| TKT-030 | Non-English message — Urdu | Detect language; respond in Urdu; use Urdu template | `test_whatsapp_handler.py` |
| TKT-031 | Billing — invoice history not visible | Guide: Settings → Billing → Invoice History | `test_whatsapp_handler.py` |
| TKT-032 | Gibberish / empty / test message | Do not create ticket; log as invalid; no response sent | `test_whatsapp_handler.py::test_media_only_message_gets_placeholder` |
| TKT-033 | Feature — remove workspace member | Steps: Settings → Team → Members → Remove | `test_whatsapp_handler.py` |
| TKT-034 | Notification overload complaint | Guide: notification preferences in profile settings | `test_whatsapp_handler.py` |
| TKT-035 | 2FA setup question | Step-by-step 2FA enable via Security settings | `test_whatsapp_handler.py` |
| TKT-036 | Bug — CSV task import failed | Check file format requirements; provide template link | `test_whatsapp_handler.py` |
| TKT-037 | Cosmetic feature — workspace theme | Explain theme options in Settings → Appearance | `test_whatsapp_handler.py` |
| TKT-038 | Angry customer — past downtime complaint | Empathize; acknowledge incident; offer SLA credit if applicable; escalate | `test_whatsapp_handler.py` |
| TKT-039 | Multi-channel Slack connection | Confirm multi-workspace Slack support; link docs | `test_whatsapp_handler.py` |
| TKT-040 | Sales inquiry via WhatsApp | Escalate to sales team; not agent scope | `test_whatsapp_handler.py` |

---

## Web Form Channel (TKT-041 to TKT-060)

| Ticket ID | Edge Case Type | Expected Behavior | Test Exists |
|-----------|---------------|-------------------|-------------|
| TKT-041 | Auth bug — account not found | Verify email; check if registered; offer password reset | `test_e2e.py::test_web_form_e2e` |
| TKT-042 | Onboarding — dev team workspace setup | Multi-step onboarding guide for technical teams | `test_e2e.py::test_web_form_e2e` |
| TKT-043 | Non-English — Spanish message | Detect Spanish; respond in Spanish | `test_e2e.py` |
| TKT-044 | GDPR / data privacy compliance | Escalate — legal/compliance outside agent scope | `test_e2e.py::test_escalation_path` |
| TKT-045 | Billing — feature loss after plan downgrade | Explain which features require Growth/Enterprise; offer upgrade path | `test_e2e.py` |
| TKT-046 | Urgent — all automations failing | High priority; immediate troubleshoot; escalate if unresolved in 2 steps | `test_e2e.py::test_escalation_path` |
| TKT-047 | Feature — recurring tasks setup | Step guide: New Task → Recurrence → frequency options | `test_e2e.py` |
| TKT-048 | Feature — bulk delete tasks | Explain bulk select + delete via task list view | `test_e2e.py` |
| TKT-049 | Integration — Zapier question | Confirm Zapier integration; link setup docs | `test_e2e.py` |
| TKT-050 | Cross-channel follow-up — same Slack issue | Detect prior history; reference previous ticket; continue resolution | `test_e2e.py::test_cross_channel_identity` |
| TKT-051 | Very long message — complex multi-issue ticket | Handle multi-topic message; address each item; escalate complex parts | `test_e2e.py` |
| TKT-052 | Follow-up on prior ticket — automation still broken | Retrieve conversation history; escalate persistent issue | `test_e2e.py::test_cross_channel_identity` |
| TKT-053 | Onboarding — account verification flow | Guide verification email steps; offer resend | `test_e2e.py` |
| TKT-054 | API docs access issue | Provide direct link to API docs; check plan tier for API access | `test_e2e.py` |
| TKT-055 | Discount request — non-profit | Escalate to sales — pricing decisions outside agent scope | `test_e2e.py::test_escalation_path` |
| TKT-056 | Billing access lost — owner left company | Escalate — account ownership transfer requires verification | `test_e2e.py::test_escalation_path` |
| TKT-057 | Bug — tasks disappearing after update | Escalate — data integrity issue; check backup restore options | `test_e2e.py` |
| TKT-058 | Plan limit hit — Starter automation cap | Explain 5-rule Starter limit; offer Growth upgrade | `test_e2e.py` |
| TKT-059 | Positive feedback + feature suggestion | Acknowledge; thank customer; log feature request | `test_e2e.py` |
| TKT-060 | Security incident — unauthorized access | Escalate IMMEDIATELY — security incident protocol; lock account | `test_e2e.py::test_escalation_path` |

---

## Edge Case Categories Summary

| Category | Count | Channels |
|----------|-------|---------|
| Bug / technical issue | 14 | All 3 |
| Feature question | 16 | All 3 |
| Billing / subscription | 10 | All 3 |
| Escalation (refund, angry, security, legal) | 12 | All 3 |
| Onboarding | 6 | All 3 |
| Non-English input | 2 | WhatsApp, Web Form |
| Cross-channel follow-up | 2 | Web Form |
