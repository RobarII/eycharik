export interface RunSummary {
  run_id: string;
  employee_id: string;
  name: string;
  role: string;
  department: string;
  step_id: string;
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
