import type {
  Defect,
  DefectsResponse,
  StatsResponse,
  BurndownResponse,
  AgingResponse,
  VelocityResponse,
  PriorityTrendResponse,
  ExecutiveResponse,
  KanbanResponse,
} from "./types";

const BASE_URL = "/api";

export interface DefectsParams {
  status?: string;
  priority?: string;
  owner?: string;
  module?: string;
  workstream?: string;
  defect_type?: string;
  page?: number;
  limit?: number;
  q?: string;
}

export async function fetchDefects(
  params: DefectsParams = {},
): Promise<DefectsResponse> {
  const searchParams = new URLSearchParams();

  if (params.status) searchParams.set("status", params.status);
  if (params.priority) searchParams.set("priority", params.priority);
  if (params.owner) searchParams.set("owner", params.owner);
  if (params.module) searchParams.set("module", params.module);
  if (params.workstream) searchParams.set("workstream", params.workstream);
  if (params.defect_type) searchParams.set("defect_type", params.defect_type);
  if (params.page) searchParams.set("page", params.page.toString());
  if (params.limit) searchParams.set("limit", params.limit.toString());
  if (params.q) searchParams.set("q", params.q);

  const url = `${BASE_URL}/defects?${searchParams}`;
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`Failed to fetch defects: ${res.status}`);
  }

  return res.json();
}

export async function fetchDefect(id: number): Promise<Defect> {
  const res = await fetch(`${BASE_URL}/defects/${id}`);

  if (!res.ok) {
    throw new Error(`Failed to fetch defect: ${res.status}`);
  }

  return res.json();
}

export async function searchDefects(query: string): Promise<DefectsResponse> {
  return fetchDefects({ q: query });
}

export async function fetchStats(
  includeClosed: boolean = false,
): Promise<StatsResponse> {
  const url = `${BASE_URL}/stats?include_closed=${includeClosed}`;
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`Failed to fetch stats: ${res.status}`);
  }

  return res.json();
}

export async function fetchBurndown(): Promise<BurndownResponse> {
  const res = await fetch(`${BASE_URL}/burndown`);

  if (!res.ok) {
    throw new Error(`Failed to fetch burndown: ${res.status}`);
  }

  return res.json();
}

export async function fetchAging(): Promise<AgingResponse> {
  const res = await fetch(`${BASE_URL}/aging`);

  if (!res.ok) {
    throw new Error(`Failed to fetch aging: ${res.status}`);
  }

  return res.json();
}

export async function fetchVelocity(): Promise<VelocityResponse> {
  const res = await fetch(`${BASE_URL}/velocity`);

  if (!res.ok) {
    throw new Error(`Failed to fetch velocity: ${res.status}`);
  }

  return res.json();
}

export async function fetchPriorityTrend(): Promise<PriorityTrendResponse> {
  const res = await fetch(`${BASE_URL}/priority-trend`);

  if (!res.ok) {
    throw new Error(`Failed to fetch priority trend: ${res.status}`);
  }

  return res.json();
}

export async function fetchExecutive(): Promise<ExecutiveResponse> {
  const res = await fetch(`${BASE_URL}/executive`);

  if (!res.ok) {
    throw new Error(`Failed to fetch executive summary: ${res.status}`);
  }

  return res.json();
}

export interface KanbanParams {
  lane?: string;
  include_hidden?: boolean;
}

export async function fetchKanban(
  params: KanbanParams = {},
): Promise<KanbanResponse> {
  const searchParams = new URLSearchParams();

  if (params.lane) searchParams.set("lane", params.lane);
  if (params.include_hidden) searchParams.set("include_hidden", "true");

  const url = `${BASE_URL}/kanban?${searchParams}`;
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`Failed to fetch kanban: ${res.status}`);
  }

  return res.json();
}
