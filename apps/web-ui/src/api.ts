export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function detailMessage(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "请求失败";
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : ""))
      .filter(Boolean)
      .join("；");
  }
  return "请求失败";
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, detailMessage(payload) || "请求失败");
  return payload as T;
}

export interface ServerSummary {
  id: string;
  name: string;
  intranet_host: string;
  ssh_port: number;
  ssh_user: string;
  auth_method: "private_key" | "password";
  ssh_key_id: string | null;
  ssh_key_name: string | null;
  host_key_fingerprint: string | null;
  docker_version: string | null;
  compose_version: string | null;
  reachability: string;
  last_checked_at: string | null;
  container_count: number | null;
  created_at: string;
}

export interface ContainerRow {
  container_id: string;
  name: string;
  image: string;
  status: string;
  ports: string;
  managed: boolean;
  strategy_slug: string | null;
  observed_at: string;
}

export interface Job {
  id: string;
  server_id: string;
  action: string;
  status: string;
  output_excerpt: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ServerDetail extends ServerSummary {
  containers: ContainerRow[];
  recent_jobs: Job[];
}

export const reachabilityLabel: Record<string, string> = {
  online: "在线",
  offline: "离线",
  docker_unavailable: "Docker 不可用",
  unknown: "未检查",
};

export const containerStatusLabel: Record<string, string> = {
  running: "运行中",
  exited: "已退出",
  restarting: "重启中",
  paused: "已暂停",
  created: "已创建",
  dead: "已停止",
};

export const jobStatusLabel: Record<string, string> = {
  queued: "排队",
  running: "执行中",
  succeeded: "成功",
  failed: "失败",
};

export const jobActionLabel: Record<string, string> = {
  test_connection: "测试连接",
  inspect: "刷新容器",
};

export function formatTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
