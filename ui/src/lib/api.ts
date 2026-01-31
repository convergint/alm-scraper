import type { Defect, DefectsResponse } from './types';

const BASE_URL = '/api';

export interface DefectsParams {
	status?: string;
	priority?: string;
	owner?: string;
	module?: string;
	page?: number;
	limit?: number;
	q?: string;
}

export async function fetchDefects(params: DefectsParams = {}): Promise<DefectsResponse> {
	const searchParams = new URLSearchParams();

	if (params.status) searchParams.set('status', params.status);
	if (params.priority) searchParams.set('priority', params.priority);
	if (params.owner) searchParams.set('owner', params.owner);
	if (params.module) searchParams.set('module', params.module);
	if (params.page) searchParams.set('page', params.page.toString());
	if (params.limit) searchParams.set('limit', params.limit.toString());
	if (params.q) searchParams.set('q', params.q);

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
