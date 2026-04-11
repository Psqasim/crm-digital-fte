export type TicketStatus = "open" | "in_progress" | "resolved" | "escalated";

export interface TicketMessage {
  role: "customer" | "assistant" | "agent";
  content: string;
  created_at: string;
  is_human_agent: boolean;
}

export interface TicketData {
  ticket_id: string;
  internal_id: string;
  status: TicketStatus;
  category: string | null;
  priority: string;
  subject: string | null;
  message: string | null;
  ai_response: string | null;
  messages?: TicketMessage[];
  customer_name: string;
  customer_email: string;
  created_at: string;
  updated_at: string | null;
  resolved_at: string | null;
}

export interface ChannelBreakdown {
  [channel: string]: number;
}

export interface RecentTicket {
  ticket_id: string;
  status: TicketStatus;
  category: string | null;
  priority: string;
  subject: string | null;
  created_at: string;
  customer_name: string;
}

export interface MetricsSummary {
  total: number;
  open: number;
  in_progress: number;
  resolved: number;
  escalated: number;
  escalation_rate: number;
  channels: ChannelBreakdown;
  recent_tickets: RecentTicket[];
}

export interface FormPayload {
  name: string;
  email: string;
  subject: string;
  message: string;
  priority?: string;
}

export interface TicketResponse {
  ticket_id: string;
  status: TicketStatus;
  message: string;
  estimated_response_time?: string;
}
