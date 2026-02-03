export interface Defect {
  id: number;
  name: string;
  status: string | null;
  priority: string | null;
  severity: string | null;
  owner: string | null;
  detected_by: string | null;
  description: string | null;
  description_html: string | null;
  dev_comments: string | null;
  dev_comments_html: string | null;
  created: string | null;
  modified: string | null;
  closed: string | null;
  reproducible: string | null;
  attachment: string | null;
  detected_in_rel: string | null;
  detected_in_rcyc: string | null;
  actual_fix_time: number | null;
  defect_type: string | null;
  application: string | null;
  workstream: string | null;
  module: string | null;
  target_date: string | null;
  // Extracted scenario codes
  scenarios: string[];
  blocks: string[];
  integrations: string[];
  clean_name: string | null;
}

export interface DefectsResponse {
  defects: Defect[];
  total: number;
  page: number;
  pages: number;
}

export interface NameCount {
  name: string;
  count: number;
}

export interface OldestDefect {
  id: number;
  name: string;
  created: string;
}

export interface CloseTimeStats {
  p50: number;
  p75: number;
  avg: number;
}

export interface StatsResponse {
  total: number;
  open_count: number;
  closed_count: number;
  by_priority: NameCount[];
  by_module: NameCount[];
  by_owner: NameCount[];
  by_type: NameCount[];
  by_workstream: NameCount[];
  by_scenario: NameCount[];
  oldest_open: OldestDefect | null;
  close_time: CloseTimeStats | null;
}

export interface BurndownPrediction {
  dates: string[];
  open_count: number[];
  daily_open_rate: number;
  daily_close_rate: number;
  net_burn_rate: number;
}

export interface BurndownResponse {
  dates: string[];
  cumulative_opened: number[];
  cumulative_closed: number[];
  open_count: number[];
  prediction: BurndownPrediction | null;
}

export interface AgingByPriority {
  priority: string;
  "0-7 days": number;
  "8-30 days": number;
  "31-90 days": number;
  "90+ days": number;
}

export interface OldestDefect {
  id: number;
  name: string;
  created: string;
  priority: string | null;
  age_days: number;
}

export interface AgingResponse {
  buckets: Record<string, number>;
  by_priority: AgingByPriority[];
  oldest: OldestDefect[];
}

export interface WeeklyVelocity {
  week: string;
  opened: number;
  resolved: number;
  net: number;
}

export interface VelocityResponse {
  weeks: WeeklyVelocity[];
  avg_opened_per_week: number;
  avg_resolved_per_week: number;
  avg_net_per_week: number;
}

export interface PriorityWeek {
  week: string;
  P1: number;
  P2: number;
  P3: number;
  P4: number;
  total: number;
}

export interface PriorityTrendResponse {
  weeks: PriorityWeek[];
}

// Executive summary types
export interface OwnershipStats {
  active: number;
  p1: number;
  p2: number;
}

export interface PipelineStatus {
  status: string;
  count: number;
  avg_days_stale: number;
}

export interface BlockedDefect {
  id: number;
  name: string;
  owner: string | null;
  priority: string | null;
  age_days: number;
  days_stale: number;
}

export interface ConvergintOwner {
  owner: string;
  owner_raw: string;
  active: number;
  high_priority: number;
  max_days_stale: number;
  avg_age: number;
}

export interface StaleDefect {
  id: number;
  name: string;
  owner: string;
  priority: string | null;
  status: string;
  age_days: number;
  days_stale: number;
}

export interface HighPriorityStale {
  id: number;
  name: string;
  owner: string | null;
  priority: string;
  age_days: number;
}

export interface ExecutiveResponse {
  ownership: Record<string, OwnershipStats>;
  pipeline: PipelineStatus[];
  blocked: BlockedDefect[];
  blocked_count: number;
  convergint_owners: ConvergintOwner[];
  stale_convergint: StaleDefect[];
  high_priority_stale: HighPriorityStale[];
}

// Kanban types
export interface KanbanDefect {
  id: number;
  name: string;
  status: string | null;
  priority: string | null;
  owner: string | null;
  module: string | null;
  workstream: string | null;
  created: string | null;
  modified: string | null;
}

export interface KanbanResponse {
  columns: string[];
  defects: KanbanDefect[];
  lanes: string[];
  lane_field: string | null;
}
