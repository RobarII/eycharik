import type {
  AdminIdentity,
  AnalyticsOverview,
  DigestResponse,
  KnowledgeDocument,
  KnowledgeExtraction,
  KnowledgeFileQueued,
  KnowledgeUploaded,
  ListResponse,
  OffboardedEmployee,
  Page,
  AssignedQuestion,
  Question,
  ResolvedQuestion,
  RunDetail,
  RunSummary,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

/** The server does not know this session any more: the caller must go back to the gate. */
export class Unauthorized extends Error {
  constructor() {
    super("Нужен доступ");
    this.name = "Unauthorized";
  }
}

/** A refused request that is not an expired session. `status` drives the message. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function detail(response: Response): Promise<string | null> {
  const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
  return typeof body?.detail === "string" ? body.detail : null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { credentials: "same-origin", ...init });
  if (response.status === 401) throw new Unauthorized();
  if (!response.ok) {
    throw new ApiError(response.status, (await detail(response)) ?? `Ошибка ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/**
 * Trade the token for an HttpOnly cookie.
 *
 * The token is not stored anywhere in the page: it goes out in one body and comes back as a cookie
 * the script cannot read. See `docs/decisions/0018`.
 */
export function openSession(token: string): Promise<void> {
  return post<void>("/admin/api/session", { token });
}

export function closeSession(): Promise<void> {
  return request<void>("/admin/api/session", { method: "DELETE" });
}

export function fetchMe(): Promise<AdminIdentity> {
  return request<AdminIdentity>("/admin/api/me");
}

export type RunStatus = "active" | "completed" | "all";

export interface RunQuery {
  limit?: number;
  cursor?: string | null;
  status?: RunStatus;
  q?: string;
}

export function fetchRuns(query: RunQuery = {}): Promise<Page<RunSummary>> {
  const params = new URLSearchParams({ limit: String(query.limit ?? 50) });
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.status) params.set("status", query.status);
  if (query.q) params.set("q", query.q);
  return request(`/admin/api/runs?${params.toString()}`);
}

export function fetchRun(runId: string): Promise<RunDetail> {
  return request(`/admin/api/runs/${encodeURIComponent(runId)}`);
}

/** `me` and `unassigned` are resolved by the server: the page never filters an assignee in the browser. */
export type QuestionOwner = "any" | "me" | "unassigned";

export interface QuestionQuery {
  status: "unanswered" | "answered" | "all";
  limit?: number;
  cursor?: string | null;
  assignee?: QuestionOwner;
}

export function fetchQuestions(query: QuestionQuery): Promise<Page<Question>> {
  const params = new URLSearchParams({
    status: query.status,
    limit: String(query.limit ?? 50),
  });
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.assignee && query.assignee !== "any") params.set("assignee", query.assignee);
  return request(`/admin/api/questions?${params.toString()}`);
}

export function fetchOverview(): Promise<AnalyticsOverview> {
  return request("/admin/api/analytics/overview");
}

export function fetchDigest(days = 7): Promise<DigestResponse> {
  return request(`/admin/api/digest/weekly?days=${days}`);
}

export function fetchKnowledge(): Promise<ListResponse<KnowledgeDocument>> {
  return request("/admin/api/knowledge");
}

export function uploadKnowledge(text: string): Promise<KnowledgeUploaded> {
  return post<KnowledgeUploaded>("/admin/api/knowledge", { text });
}

export interface FileMetadata {
  id: string;
  title: string;
  owner: string;
  audience: string[];
  valid_from: string;
}

/** A PDF or a deck: the API stores it by hash and the worker extracts it out of band. */
export function uploadKnowledgeFile(
  file: File,
  metadata: FileMetadata,
): Promise<KnowledgeFileQueued> {
  const body = new FormData();
  body.append("file", file);
  body.append("metadata", JSON.stringify({ ...metadata, type: "knowledge", status: "active" }));
  return request<KnowledgeFileQueued>("/admin/api/knowledge/files", {
    method: "POST",
    body,
  });
}

export function fetchExtraction(contentHash: string): Promise<KnowledgeExtraction> {
  return request(`/admin/api/knowledge/files/${encodeURIComponent(contentHash)}`);
}

/** `null` clears the owner. Any role that may answer may also claim. */
export function assignQuestion(id: number, assignee: string | null): Promise<AssignedQuestion> {
  return request(`/admin/api/questions/${id}/assignee`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assignee }),
  });
}

export function resolveQuestion(id: number, text: string): Promise<ResolvedQuestion> {
  return post<ResolvedQuestion>(`/admin/api/questions/${id}/resolve`, { text });
}

export function offboardEmployee(employeeId: string): Promise<OffboardedEmployee> {
  return request(`/admin/api/employees/${encodeURIComponent(employeeId)}`, {
    method: "DELETE",
  });
}
