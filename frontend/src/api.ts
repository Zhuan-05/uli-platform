// Typed client for the ULI Core HTTP API. The UI talks to nothing else.

export interface AppSummary {
  id: string;
  name: string;
  version: string;
  state: string;
  trust: string;
  runtimeType: string;
  path: string;
  port: number | null;
  pid: number | null;
  isBuiltin: boolean;
  lastError: string | null;
  provides: string[];
  requires: string[];
  permissions: string[];
  frontend: string | null;
  description: string;
}

export interface CapabilityDescriptor {
  id: string;
  version: string;
  appId: string;
  appName: string;
  appState: string;
  description: string;
  inputType: string;
  outputType: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
  timeoutMs: number;
}

export interface ConnectedEdge {
  edgeId: string;
  source: string;
  target: string;
  ok: boolean;
  reason: string;
}

export interface BlueprintNode {
  id: string;
  kind: "input" | "capability" | "output";
  label?: string;
  position?: { x: number; y: number };
  capability?: string;
  appId?: string;
  inputType?: string;
  outputType?: string;
  sample?: Record<string, unknown>;
  config?: Record<string, unknown>;
}

export interface Blueprint {
  blueprintVersion: "1.0";
  id: string;
  name: string;
  version: string;
  description?: string;
  nodes: BlueprintNode[];
  edges: { id: string; source: string; target: string; sourcePort?: string; targetPort?: string }[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const text = await res.text();
  let body: any = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const detail = body?.detail ?? body ?? res.statusText;
    const message = typeof detail === "string" ? detail : JSON.stringify(detail);
    throw new Error(message);
  }
  return body as T;
}

const post = <T,>(p: string, body?: unknown) =>
  req<T>(p, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => req<any>("/api/health"),
  runtimeTypes: () => req<any>("/api/runtime-types"),
  guarantees: () => req<any>("/api/compatibility/guarantees"),

  listApps: () => req<AppSummary[]>("/api/apps"),
  getApp: (id: string) => req<any>(`/api/apps/${id}`),
  register: (path: string, trust: string, upgrade = false) =>
    post<any>("/api/apps/register", { path, trust, upgrade }),
  importStatic: (name: string, path: string, id?: string) =>
    post<any>("/api/apps/import-static", { name, path, id }),
  registerExternal: (name: string, url: string, id?: string) =>
    post<any>("/api/apps/register-external", { name, url, id }),
  enable: (id: string) => post<any>(`/api/apps/${id}/enable`),
  disable: (id: string) => post<any>(`/api/apps/${id}/disable`),
  start: (id: string) => post<any>(`/api/apps/${id}/start`),
  stop: (id: string) => post<any>(`/api/apps/${id}/stop`),
  restart: (id: string) => post<any>(`/api/apps/${id}/restart`),
  appHealth: (id: string) => req<any>(`/api/apps/${id}/health`),
  embedCheck: (id: string) => req<any>(`/api/apps/${id}/embed-check`),
  uninstall: (id: string, deleteFiles = false) =>
    req<any>(`/api/apps/${id}?deleteFiles=${deleteFiles}`, { method: "DELETE" }),

  listCapabilities: () => req<CapabilityDescriptor[]>("/api/capabilities"),
  invoke: (capability: string, input: Record<string, unknown>) =>
    post<any>(`/api/capabilities/${capability}/invoke`, { input }),
  validateConnection: (sourceOutputType: string, targetInputType: string) =>
    post<{ compatible: boolean; reason: string }>("/api/capabilities/validate-connection", {
      sourceOutputType,
      targetInputType,
    }),

  events: (limit = 50) => req<any[]>(`/api/events?limit=${limit}`),
  publish: (name: string, version: string, payload: Record<string, unknown>) =>
    post<any>("/api/events/publish", { name, version, payload }),

  listBlueprints: () => req<Blueprint[]>("/api/blueprints"),
  getBlueprint: (id: string) => req<Blueprint>(`/api/blueprints/${id}`),
  saveBlueprint: (bp: Blueprint) => post<Blueprint>("/api/blueprints", bp),
  deleteBlueprint: (id: string) => req<any>(`/api/blueprints/${id}`, { method: "DELETE" }),
  validateBlueprint: (bp: Blueprint) =>
    post<{ valid: boolean; errors: string[]; issues: ConnectedEdge[] }>("/api/blueprints/validate", bp),
  executeBlueprint: (id: string, input: Record<string, unknown>) =>
    post<any>(`/api/blueprints/${id}/execute`, { input }),

  listThemes: () => req<{ active: string; themes: any[] }>("/api/themes"),
  getTheme: (id: string) => req<any>(`/api/themes/${id}`),
  activateTheme: (id: string) => post<any>(`/api/themes/${id}/activate`),
};
