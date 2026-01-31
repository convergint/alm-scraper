<script lang="ts">
	import { fetchDefect } from '$lib/api';
	import type { Defect } from '$lib/types';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	let defect: Defect | null = $state(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleString();
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

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			goto('/');
		}
	}

	$effect(() => {
		const id = parseInt($page.params.id);
		if (isNaN(id)) {
			error = 'Invalid defect ID';
			loading = false;
			return;
		}

		fetchDefect(id)
			.then((d) => {
				defect = d;
				loading = false;
			})
			.catch((e) => {
				error = e instanceof Error ? e.message : 'Failed to load defect';
				loading = false;
			});
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<svelte:head>
	<title>{defect ? `#${defect.id}: ${defect.name}` : 'Loading...'} - ALM Defects</title>
</svelte:head>

<div class="container mx-auto px-4 py-8 max-w-4xl">
	<!-- Back button -->
	<a href="/" class="text-blue-400 hover:text-blue-300 mb-6 inline-block">
		&larr; Back to list
	</a>

	{#if loading}
		<div class="text-center py-12 text-gray-400">Loading...</div>
	{:else if error}
		<div class="text-center py-12 text-red-400">{error}</div>
	{:else if defect}
		<!-- Header -->
		<div class="mb-8">
			<div class="text-gray-400 mb-2">#{defect.id}</div>
			<h1 class="text-2xl font-bold mb-4">{defect.name}</h1>

			<div class="flex flex-wrap gap-4">
				<span class="px-3 py-1 rounded {defect.status === 'Open' ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-300'}">
					{defect.status || 'Unknown'}
				</span>
				<span class="px-3 py-1 rounded bg-gray-800 {getPriorityColor(defect.priority)}">
					{defect.priority || 'No priority'}
				</span>
			</div>
		</div>

		<!-- Metadata grid -->
		<div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8 p-4 bg-gray-800 rounded-lg">
			<div>
				<div class="text-gray-400 text-sm">Owner</div>
				<div>{stripDomain(defect.owner)}</div>
			</div>
			<div>
				<div class="text-gray-400 text-sm">Detected By</div>
				<div>{stripDomain(defect.detected_by)}</div>
			</div>
			<div>
				<div class="text-gray-400 text-sm">Severity</div>
				<div>{defect.severity || '-'}</div>
			</div>
			<div>
				<div class="text-gray-400 text-sm">Type</div>
				<div>{defect.defect_type || '-'}</div>
			</div>
			<div>
				<div class="text-gray-400 text-sm">Module</div>
				<div>{defect.module || '-'}</div>
			</div>
			<div>
				<div class="text-gray-400 text-sm">Workstream</div>
				<div>{defect.workstream || '-'}</div>
			</div>
			<div>
				<div class="text-gray-400 text-sm">Created</div>
				<div>{formatDate(defect.created)}</div>
			</div>
			<div>
				<div class="text-gray-400 text-sm">Modified</div>
				<div>{formatDate(defect.modified)}</div>
			</div>
			<div>
				<div class="text-gray-400 text-sm">Closed</div>
				<div>{formatDate(defect.closed)}</div>
			</div>
		</div>

		<!-- Description -->
		{#if defect.description}
			<div class="mb-8">
				<h2 class="text-lg font-semibold mb-3 text-gray-300">Description</h2>
				<div class="p-4 bg-gray-800 rounded-lg html-content">
					{@html defect.description}
				</div>
			</div>
		{/if}

		<!-- Dev Comments -->
		{#if defect.dev_comments}
			<div class="mb-8">
				<h2 class="text-lg font-semibold mb-3 text-gray-300">Dev Comments</h2>
				<div class="p-4 bg-gray-800 rounded-lg html-content">
					{@html defect.dev_comments}
				</div>
			</div>
		{/if}

		<!-- Additional details -->
		<div class="text-sm text-gray-500">
			<p>Press <kbd class="px-2 py-1 bg-gray-700 rounded">Esc</kbd> to return to list</p>
		</div>
	{/if}
</div>
