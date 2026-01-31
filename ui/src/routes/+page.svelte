<script lang="ts">
	import { fetchDefects, type DefectsParams } from '$lib/api';
	import type { Defect, DefectsResponse } from '$lib/types';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	let data: DefectsResponse | null = $state(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Filter state
	let status = $state('open');
	let priority = $state('');
	let owner = $state('');
	let search = $state('');
	let currentPage = $state(1);

	async function loadDefects() {
		loading = true;
		error = null;

		try {
			const params: DefectsParams = {
				page: currentPage,
				limit: 50
			};

			if (status) params.status = status;
			if (priority) params.priority = priority;
			if (owner) params.owner = owner;
			if (search) params.q = search;

			data = await fetchDefects(params);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	function handleFilterChange() {
		currentPage = 1;
		loadDefects();
	}

	function handleSearch(e: Event) {
		e.preventDefault();
		handleFilterChange();
	}

	function goToPage(page: number) {
		currentPage = page;
		loadDefects();
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleDateString();
	}

	function stripDomain(owner: string | null): string {
		if (!owner) return '-';
		return owner.includes('_') ? owner.split('_')[0] : owner;
	}

	function getPriorityColor(priority: string | null): string {
		if (!priority) return 'text-gray-400';
		if (priority.includes('1')) return 'text-red-400';
		if (priority.includes('2')) return 'text-orange-400';
		if (priority.includes('3')) return 'text-yellow-400';
		return 'text-gray-400';
	}

	// Load on mount
	$effect(() => {
		loadDefects();
	});
</script>

<svelte:head>
	<title>ALM Defects</title>
</svelte:head>

<div class="container mx-auto px-4 py-8">
	<h1 class="text-3xl font-bold mb-8">ALM Defects</h1>

	<!-- Filters -->
	<form onsubmit={handleSearch} class="mb-6 flex flex-wrap gap-4">
		<input
			type="text"
			bind:value={search}
			placeholder="Search..."
			class="bg-gray-800 border border-gray-700 rounded px-4 py-2 focus:outline-none focus:border-blue-500"
		/>

		<select
			bind:value={status}
			onchange={handleFilterChange}
			class="bg-gray-800 border border-gray-700 rounded px-4 py-2 focus:outline-none focus:border-blue-500"
		>
			<option value="">All Status</option>
			<option value="open">Open</option>
			<option value="closed">Closed</option>
			<option value="rejected">Rejected</option>
		</select>

		<select
			bind:value={priority}
			onchange={handleFilterChange}
			class="bg-gray-800 border border-gray-700 rounded px-4 py-2 focus:outline-none focus:border-blue-500"
		>
			<option value="">All Priority</option>
			<option value="P1">P1 - Critical</option>
			<option value="P2">P2 - High</option>
			<option value="P3">P3 - Medium</option>
			<option value="P4">P4 - Low</option>
		</select>

		<button
			type="submit"
			class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded font-medium"
		>
			Search
		</button>
	</form>

	<!-- Loading / Error states -->
	{#if loading}
		<div class="text-center py-12 text-gray-400">Loading...</div>
	{:else if error}
		<div class="text-center py-12 text-red-400">{error}</div>
	{:else if data}
		<!-- Results count -->
		<div class="mb-4 text-gray-400">
			Showing {data.defects.length} of {data.total} defects (page {data.page} of {data.pages})
		</div>

		<!-- Defects table -->
		<div class="overflow-x-auto">
			<table class="w-full text-left">
				<thead class="border-b border-gray-700">
					<tr>
						<th class="py-3 px-4 font-medium">ID</th>
						<th class="py-3 px-4 font-medium">Name</th>
						<th class="py-3 px-4 font-medium">Status</th>
						<th class="py-3 px-4 font-medium">Priority</th>
						<th class="py-3 px-4 font-medium">Owner</th>
						<th class="py-3 px-4 font-medium">Created</th>
					</tr>
				</thead>
				<tbody>
					{#each data.defects as defect}
						<tr
							class="border-b border-gray-800 hover:bg-gray-800 cursor-pointer"
							onclick={() => goto(`/defects/${defect.id}`)}
						>
							<td class="py-3 px-4 text-blue-400">#{defect.id}</td>
							<td class="py-3 px-4">{defect.name}</td>
							<td class="py-3 px-4">
								<span class="px-2 py-1 rounded text-sm {defect.status === 'Open' ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-300'}">
									{defect.status || '-'}
								</span>
							</td>
							<td class="py-3 px-4 {getPriorityColor(defect.priority)}">{defect.priority || '-'}</td>
							<td class="py-3 px-4">{stripDomain(defect.owner)}</td>
							<td class="py-3 px-4 text-gray-400">{formatDate(defect.created)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Pagination -->
		{#if data.pages > 1}
			<div class="mt-6 flex justify-center gap-2">
				<button
					onclick={() => goToPage(currentPage - 1)}
					disabled={currentPage === 1}
					class="px-4 py-2 bg-gray-800 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700"
				>
					Previous
				</button>
				<span class="px-4 py-2">
					Page {currentPage} of {data.pages}
				</span>
				<button
					onclick={() => goToPage(currentPage + 1)}
					disabled={currentPage === data.pages}
					class="px-4 py-2 bg-gray-800 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700"
				>
					Next
				</button>
			</div>
		{/if}
	{/if}
</div>
