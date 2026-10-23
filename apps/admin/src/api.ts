import type {
  AnalyticsOverview,
  DigestResponse,
  KnowledgeDocument,
  KnowledgeUploaded,
  ListResponse,
  Question,
  ResolvedQuestion,
  RunDetail,
  RunSummary,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
const KEY = "onboarding.admin.token";

export class Unauthorized extends Error {
  constructor() {
    super("Нужен доступ");
    this.name = "Unauthorized";
  }
}

export function getToken(): string {
  return localStorage.getItem(KEY) ?? "";
}

export function setToken(token: string): void {
  if (token) localStorage.setItem(KEY, token);
  else localStorage.removeItem(KEY);
}

async function get<T>(path: string): Promise<T> {
  const token = getToken();
  const response = await fetch(`${BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (response.status === 401) throw new Unauthorized();
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Ошибка ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchRuns(limit = 50): Promise<ListResponse<RunSummary>> {
  return get(`/admin/api/runs?limit=${limit}`);
}

export function fetchRun(runId: string): Promise<RunDetail> {
  return get(`/admin/api/runs/${encodeURIComponent(runId)}`);
}

export function fetchQuestions(
  status: "unanswered" | "answered" | "all",
  limit = 50,
): Promise<ListResponse<Question>> {
  return get(`/admin/api/questions?status=${status}&limit=${limit}`);
}

export function fetchOverview(): Promise<AnalyticsOverview> {
  return get("/admin/api/analytics/overview");
}

export function fetchDigest(days = 7): Promise<DigestResponse> {
  return get(`/admin/api/digest/weekly?days=${days}`);
}

async function send<T>(path: string, body: unknown): Promise<T> {
  const token = getToken();
  const response = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (response.status === 401) throw new Unauthorized();
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Ошибка ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchKnowledge(): Promise<ListResponse<KnowledgeDocument>> {
  return get("/admin/api/knowledge");
}

export function uploadKnowledge(text: string): Promise<KnowledgeUploaded> {
  return send("/admin/api/knowledge", { text });
}

export function resolveQuestion(id: number, text: string): Promise<ResolvedQuestion> {
  return send(`/admin/api/questions/${id}/resolve`, { text });
}
