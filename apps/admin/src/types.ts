export interface RunSummary {
  run_id: string;
  employee_id: string;
  name: string;
  role: string;
  department: string;
  step_id: string;
  step_title: string | null;
  step_number: number;
  steps_total: number;
  entered_at: string;
  status: "active" | "completed";
}

export interface AuditEvent {
  name: string;
  at: string;
  fields: Record<string, unknown>;
}

export interface Question {
  employee_id: string;
  employee_name: string;
  text: string;
  answered: boolean;
  reason: string;
  citations: string[];
  asked_at: string;
}

export interface RunDetail extends RunSummary {
  step_message: string | null;
  scenario: string;
  scenario_version: number;
  events: AuditEvent[];
  questions: Question[];
}

export interface ListResponse<T> {
  items: T[];
}


export interface TagCount {
  tag: string;
  count: number;
}

export interface AnalyticsOverview {
  active_runs: number;
  completed_runs: number;
  high_risk: number;
  medium_risk: number;
  unanswered_questions: number;
  top_tags: TagCount[];
  since: string;
}

export interface DigestItem {
  employee_id: string;
  employee_name: string;
  department: string;
  step_id: string;
  level: "high" | "medium";
  reasons: string[];
  tags: string[];
  at: string;
}

export interface DigestResponse {
  items: DigestItem[];
  since: string;
}
