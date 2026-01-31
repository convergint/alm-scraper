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
}

export interface DefectsResponse {
	defects: Defect[];
	total: number;
	page: number;
	pages: number;
}

export interface StatsResponse {
	total_open: number;
	total_closed: number;
	oldest_open: Defect | null;
	by_priority: Record<string, number>;
	by_owner: Record<string, number>;
	by_module: Record<string, number>;
}
