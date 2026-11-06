export type Run = { id: string; label: string; model: string };
export type Method = {
  split: string; policy: string; budget: number; tasks: number; successes: number;
  exact_correct: number; exact_accuracy: number; actual_total_tokens: number;
  context_evidence_recall: number; mean_proxy_tokens: number;
};
export type Artifact = { id: string; title: string; filename: string; bytes: number; private: boolean };
export type Usage = { total_tokens?: number; total_calls?: number; input_tokens?: number; output_tokens?: number; unknown_usage_calls?: number; failed_calls?: number };
export type Overview = {
  id: string; label: string; model: string | null; protocol: string; limits: { tokens?: number; main_budget: number };
  grid_count: number; tasks: number; test_tasks: number; dev_tasks: number; complete: boolean;
  methods: Method[]; resources: { end_to_end: Usage; experiment_only?: Usage; per_stage?: Record<string, { calls: number; tokens: number }>; currency_cost?: number | null; token_admission_limit?: number };
  review: { score: number | null; scale: number; text: string; matches_paper: boolean; retrieved_date?: string; paper_sha256?: string; paper_evaluation_agent_score?: number | null };
  paper_sha256: string | null; availability: { summary: boolean; paper: boolean; review: boolean };
  artifacts: Artifact[]; limitations: string[];
};
export type Case = {
  task_id: string; policy: string; split: string; budget: number; family: string; status: string;
  answer?: string; selected_ids?: string[]; context_text?: string; proxy_tokens?: number;
  score?: { exact: boolean; evidence_recall: number; field_accuracy: number };
  task?: { question: string; gold: Record<string, unknown>; records: Record<string, unknown>[]; query: Record<string, unknown> };
};

export async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) throw new Error(response.status === 503 ? '本地产物缺失或格式异常，请检查运行目录。' : `无法读取项目数据（${response.status}）。`);
  return response.json() as Promise<T>;
}
export const runUrl = (id: string) => `/api/runs/${encodeURIComponent(id)}`;
export const fileUrl = (id: string, file: string) => `${runUrl(id)}/files/${encodeURIComponent(file)}`;
export const number = (value?: number | null) => value == null ? '—' : new Intl.NumberFormat('en-US').format(value);
export const percent = (value?: number | null) => value == null ? '—' : `${(value * 100).toFixed(1)}%`;

export async function post<T>(path: string, body: unknown): Promise<T> {
  const { token } = await get<{ token: string }>('/api/session');
  const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Workbench-Token': token }, body: JSON.stringify(body) });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || `操作失败（${response.status}）`);
  return value as T;
}
