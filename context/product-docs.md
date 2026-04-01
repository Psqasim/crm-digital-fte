# NexaFlow — Product Documentation

## 1. Workspace Setup and Onboarding

### Creating Your Workspace
1. Sign up at app.nexaflow.io with your work email.
2. Choose a workspace name (this becomes your subdomain: `yourteam.nexaflow.io`).
3. Invite teammates by entering their emails or sharing an invite link (link expires in 48 hours).
4. Select your primary use case during onboarding (Project Management, Sales Ops, HR Workflows, IT Operations, or Custom).

### Onboarding Checklist
- [ ] Create first workflow from a template or from scratch
- [ ] Connect at least one integration (Slack recommended for notifications)
- [ ] Assign roles to teammates
- [ ] Set up your first automation rule

### Workspace Settings
- Found under **Settings > Workspace**
- Configure: timezone, date format, working hours, notification preferences
- Starter plan: 1 workspace; Growth: up to 5 workspaces; Enterprise: unlimited

---

## 2. Task Automation Rules

### Overview
Automation rules consist of three parts: **Triggers**, **Conditions**, and **Actions**.

### Triggers
- Task created
- Task status changed
- Due date approaching (configurable: 1, 2, 3, 7 days before)
- Form submission received
- Webhook received from external source
- Scheduled time (cron-style: daily, weekly, monthly)
- New team member added to workspace

### Conditions (optional filters)
- Field equals / does not equal [value]
- Field contains / does not contain [value]
- Assignee is / is not [user]
- Priority is [low/medium/high/critical]
- Tag includes [tag name]
- Custom field value comparisons

### Actions
- Create task / subtask
- Update task field
- Assign task to user or team
- Send Slack message (requires Slack integration)
- Send email notification
- Create GitHub issue (requires GitHub integration)
- Add comment to task
- Move task to another project
- Trigger webhook (POST to external URL)
- Create Jira ticket (requires Jira integration)

### Limits
- Starter: 5 active automation rules
- Growth: 50 active automation rules
- Enterprise: unlimited automation rules

---

## 3. Integrations

### Slack
- **Setup:** Settings > Integrations > Slack > "Connect to Slack" (OAuth)
- **Features:** Receive task notifications in channels, create tasks from Slack messages (/nexaflow create), daily digest summaries
- **Troubleshooting:** If Slack notifications stop, re-authenticate at Settings > Integrations > Slack > Reconnect. This is usually caused by token expiry (every 90 days).

### Jira
- **Setup:** Settings > Integrations > Jira > Enter Jira domain + API token
- **Features:** Bi-directional sync of issues and tasks, status mapping, comment sync
- **Supported:** Jira Cloud only (not Jira Server/Data Center)
- **Troubleshooting:** "Authentication failed" usually means the API token was regenerated in Jira. Generate a new token at id.atlassian.com and re-enter it in NexaFlow.

### GitHub
- **Setup:** Settings > Integrations > GitHub > Authorize via OAuth
- **Features:** Auto-create GitHub issues from tasks, link PRs to tasks, close tasks when PRs merge
- **Troubleshooting:** "Repository not found" error — ensure the GitHub user has admin access to the repo, or re-authorize the OAuth app.

### Google Calendar
- **Setup:** Settings > Integrations > Google Calendar > Connect (Google OAuth)
- **Features:** Sync task due dates as calendar events, block-off time for tasks, view task deadlines alongside meetings
- **Troubleshooting:** If events stop syncing, revoke and re-grant access at myaccount.google.com > Security > Third-party apps > NexaFlow.

---

## 4. User Permissions and Roles

| Role    | Permissions |
|---------|-------------|
| Owner   | Full control: billing, workspace deletion, all settings, all data |
| Admin   | Manage members, integrations, projects, automations; cannot manage billing |
| Member  | Create/edit tasks and workflows they are assigned to or have project access for |
| Guest   | Read-only access to specific projects they've been explicitly invited to |

### Changing Roles
- Only Owners and Admins can change roles.
- Go to **Settings > Members > [member name] > Change Role**
- Guests cannot be made Members without an email domain match or explicit Owner approval.

### Removing a Member
- Settings > Members > [member name] > Remove from Workspace
- Their created tasks remain; ownership transfers to the workspace Owner.

---

## 5. Billing

### Upgrading Your Plan
1. Go to **Settings > Billing > Change Plan**
2. Select Growth or Enterprise
3. Enter payment details (credit card or invoice for Enterprise)
4. Upgrade takes effect immediately; prorated charge applied for current month

### Downgrading Your Plan
- Can downgrade at any time; takes effect at the end of the current billing cycle
- If downgrading from Growth to Starter and you have more than 5 users, extra users become read-only until removed
- Automations above Starter limits are paused (not deleted) on downgrade

### Invoice Access
- All invoices available at **Settings > Billing > Invoice History**
- Invoices sent automatically to the billing email on the 1st of each month
- Enterprise customers can request custom billing cycles

### Cancellation Policy
- Cancel anytime from **Settings > Billing > Cancel Subscription**
- No refunds for partial months (except as described in the refund policy below)
- Data retained for 90 days post-cancellation, then permanently deleted
- Export your data before cancelling (see Data Export section)

### Refund Policy
- Refunds available within 14 days of initial purchase for annual subscriptions
- Monthly subscriptions: no refunds for partial months
- Contact support with your account email and reason; refunds processed within 5–7 business days

---

## 6. API Access

- **Available on:** Enterprise plan only
- **Type:** REST API + Webhooks
- **Base URL:** `https://api.nexaflow.io/v1`
- **Authentication:** Bearer token (generated at Settings > API > Generate Token)
- **Rate Limits:** 1,000 requests/hour per token
- **Webhook Events:** task.created, task.updated, task.completed, form.submitted, member.added
- **Docs:** Full API reference at docs.nexaflow.io/api (requires Enterprise login)
- **SDKs:** Python and Node.js SDKs available on GitHub (github.com/nexaflow/sdk)

---

## 7. Mobile App

- **iOS:** Available on App Store (iOS 15+)
- **Android:** Available on Google Play (Android 10+)
- **Features:** View and update tasks, receive push notifications, create tasks via voice, offline mode (read-only)
- **Limitations:** Automation rule creation not available on mobile; integrations must be configured on desktop
- **Sync:** Real-time sync with web app via WebSocket

---

## 8. Data Export

### Export Options
- **CSV:** Export tasks, projects, members, and activity logs
- **JSON:** Full workspace export including all metadata, custom fields, attachments list

### How to Export
1. Go to **Settings > Data & Privacy > Export Data**
2. Select export type (CSV or JSON) and scope (all data or specific project)
3. Click "Request Export" — you'll receive an email with download link within 15 minutes
4. Download link expires after 24 hours

### Notes
- Attachments are not included in CSV/JSON exports (available as separate ZIP)
- Export history retained for 30 days

---

## 9. Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Integration authentication failed" | OAuth token expired or revoked | Re-authenticate the integration at Settings > Integrations |
| "Webhook timeout" | Target server took > 10 seconds to respond | Ensure your webhook endpoint responds within 10s; check server logs |
| "Automation rule limit reached" | Exceeded plan limit for active rules | Upgrade plan or deactivate existing rules |
| "Cannot invite user — seat limit reached" | Reached max users for current plan | Upgrade plan or remove inactive members |
| "Export failed" | Workspace too large or temporary server issue | Retry after 5 minutes; contact support if persistent |
| "Slack channel not found" | Channel deleted or bot removed | Re-select Slack channel in the automation rule settings |
| "GitHub repo not accessible" | Repository permissions changed | Re-authorize GitHub integration |
| "Task import failed" | CSV format mismatch | Use the import template from Settings > Import > Download Template |
| "SSO login failed" | SAML config mismatch | Enterprise only — contact your CSM to review SAML settings |

---

## 10. Service Level Agreements (SLA)

| Plan       | First Response | Resolution Target | Dedicated CSM |
|------------|---------------|-------------------|---------------|
| Starter    | Best effort   | Best effort       | No            |
| Growth     | 24 hours      | 72 hours          | No            |
| Enterprise | 4 hours       | 24 hours          | Yes           |

- SLA clock starts from ticket submission time
- SLA pauses outside business hours for Growth plan (Mon–Fri 9am–6pm PKT)
- Enterprise SLA runs 24/7
- SLA breach compensation: one month free (Enterprise only, upon verified breach)
