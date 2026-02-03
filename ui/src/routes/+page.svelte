<script lang="ts">
	import { fetchDefects, type DefectsParams } from '$lib/api';
	import type { Defect, DefectsResponse } from '$lib/types';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Input } from '$lib/components/ui/input';
	import * as Table from '$lib/components/ui/table';
	import * as Select from '$lib/components/ui/select';
	import KeyboardShortcuts from '$lib/components/KeyboardShortcuts.svelte';

	let data: DefectsResponse | null = $state(null);
	let error = $state<string | null>(null);
	let selectedIndex = $state(-1);
	let searchInputEl: HTMLInputElement | null = $state(null);

	// Read initial filter values from URL
	const urlParams = $derived(new URLSearchParams($page.url.search));

	// Filter state - initialize from URL params
	let status = $state('!terminal');
	let priority = $state('');
	let owner = $state('');
	let workstream = $state('');
	let defectType = $state('');
	let search = $state('');
	let initialized = $state(false);

	// Initialize from URL on first load
	$effect(() => {
		if (!initialized) {
			status = urlParams.get('status') || '!terminal';
			priority = urlParams.get('priority') || '';
			owner = urlParams.get('owner') || '';
			workstream = urlParams.get('workstream') || '';
			defectType = urlParams.get('defect_type') || '';
			search = urlParams.get('q') || '';
			initialized = true;
		}
	});

	async function loadDefects() {
		error = null;

		try {
			const params: DefectsParams = {
				limit: 5000
			};

			if (status) params.status = status;
			if (priority) params.priority = priority;
			if (owner) params.owner = owner;
			if (workstream) params.workstream = workstream;
			if (defectType) params.defect_type = defectType;
			if (search) params.q = search;

			data = await fetchDefects(params);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		}
	}

	function updateUrl() {
		const params = new URLSearchParams();
		if (status && status !== '!terminal') params.set('status', status);
		if (priority) params.set('priority', priority);
		if (owner) params.set('owner', owner);
		if (workstream) params.set('workstream', workstream);
		if (defectType) params.set('defect_type', defectType);
		if (search) params.set('q', search);

		const newUrl = params.toString() ? `?${params}` : '/';
		goto(newUrl, { replaceState: true, keepFocus: true });
	}

	// Debounce URL updates for search input
	let urlUpdateTimeout: ReturnType<typeof setTimeout> | null = null;
	function debouncedUrlUpdate() {
		if (urlUpdateTimeout) clearTimeout(urlUpdateTimeout);
		urlUpdateTimeout = setTimeout(updateUrl, 300);
	}

	function handleFilterChange() {
		updateUrl();
		loadDefects();
	}

	function handleSearchInput() {
		debouncedUrlUpdate();
		loadDefects();
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toISOString().slice(0, 10);
	}

	function stripDomain(owner: string | null): string {
		if (!owner) return '-';
		return owner.includes('_') ? owner.split('_')[0] : owner;
	}

	function getPriorityIndicator(priority: string | null): { color: string; label: string } {
		if (!priority) return { color: 'bg-muted', label: '-' };
		if (priority.includes('1')) return { color: 'bg-red-500', label: 'P1' };
		if (priority.includes('2')) return { color: 'bg-orange-500', label: 'P2' };
		if (priority.includes('3')) return { color: 'bg-yellow-500', label: 'P3' };
		if (priority.includes('4')) return { color: 'bg-green-500', label: 'P4' };
		return { color: 'bg-muted', label: '-' };
	}

	// Keyboard navigation
	function navigateDown() {
		if (data && data.defects.length > 0) {
			selectedIndex = Math.min(selectedIndex + 1, data.defects.length - 1);
			scrollToSelected();
		}
	}

	function navigateUp() {
		if (data && data.defects.length > 0) {
			selectedIndex = Math.max(selectedIndex - 1, 0);
			scrollToSelected();
		}
	}

	function selectCurrent() {
		if (data && selectedIndex >= 0 && selectedIndex < data.defects.length) {
			goto(`/defects/${data.defects[selectedIndex].id}`);
		}
	}

	function scrollToSelected() {
		const row = document.querySelector(`[data-index="${selectedIndex}"]`);
		row?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
	}

	// Reset selection when data changes
	$effect(() => {
		if (data) {
			selectedIndex = data.defects.length > 0 ? 0 : -1;
		}
	});

	// Load on mount
	$effect(() => {
		loadDefects();
	});
</script>

<svelte:head>
	<title>ALM Defects</title>
</svelte:head>

<div class="container mx-auto px-4 py-8">
	<div class="mb-6">
		<h1 class="text-3xl font-bold">ALM Defects</h1>
		<p class="text-xs text-muted-foreground font-mono mt-1 h-4">{$page.url.search || ''}</p>
	</div>

	<!-- Filters -->
	<div class="mb-6 flex flex-wrap gap-4 items-end">
		<div class="flex-1 min-w-48">
			<Input
				type="text"
				bind:value={search}
				bind:ref={searchInputEl as HTMLInputElement}
				oninput={handleSearchInput}
				placeholder="Search defects..."
			/>
		</div>

		<Select.Root type="single" bind:value={status} onValueChange={handleFilterChange}>
			<Select.Trigger class="w-44">
				{#if status === '!terminal'}
					Active
				{:else if status === 'closed'}
					Closed
				{:else if status === 'open'}
					Open Only
				{:else if status === 'blocked'}
					Blocked
				{:else if status === ''}
					All Status
				{:else}
					{status}
				{/if}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="">All Status</Select.Item>
				<Select.Item value="!terminal">Active</Select.Item>
				<Select.Item value="open">Open Only</Select.Item>
				<Select.Item value="blocked">Blocked</Select.Item>
				<Select.Item value="closed">Closed</Select.Item>
			</Select.Content>
		</Select.Root>

		<Select.Root type="single" bind:value={priority} onValueChange={handleFilterChange}>
			<Select.Trigger class="w-40">
				{priority ? priority.split('-')[0] : 'All Priority'}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="">All Priority</Select.Item>
				<Select.Item value="P1-Critical">P1 - Critical</Select.Item>
				<Select.Item value="P2-High">P2 - High</Select.Item>
				<Select.Item value="P3-Medium">P3 - Medium</Select.Item>
				<Select.Item value="P4-Low">P4 - Low</Select.Item>
			</Select.Content>
		</Select.Root>

		<!-- Active filter badges -->
		{#if owner}
			<Badge variant="secondary" class="flex items-center gap-1 px-3 py-1.5">
				Owner: {owner.includes('convergint') ? 'Convergint' : owner.replace(/_/g, ' ')}
				<button
					type="button"
					onclick={() => { owner = ''; handleFilterChange(); }}
					class="ml-1 hover:text-destructive"
				>×</button>
			</Badge>
		{/if}
		{#if workstream}
			<Badge variant="secondary" class="flex items-center gap-1 px-3 py-1.5">
				Workstream: {workstream}
				<button
					type="button"
					onclick={() => { workstream = ''; handleFilterChange(); }}
					class="ml-1 hover:text-destructive"
				>×</button>
			</Badge>
		{/if}
		{#if defectType}
			<Badge variant="secondary" class="flex items-center gap-1 px-3 py-1.5">
				Type: {defectType}
				<button
					type="button"
					onclick={() => { defectType = ''; handleFilterChange(); }}
					class="ml-1 hover:text-destructive"
				>×</button>
			</Badge>
		{/if}
	</div>

	<!-- Error state -->
	{#if error}
		<div class="text-center py-12 text-destructive">{error}</div>
	{:else if data}
		<!-- Results count -->
		<div class="mb-4 text-muted-foreground">
			{data.defects.length} defects
		</div>

		<!-- Defects table -->
		<Table.Root>
			<Table.Header>
				<Table.Row>
					<Table.Head class="w-16">ID</Table.Head>
					<Table.Head>Name</Table.Head>
					<Table.Head class="w-28">Status</Table.Head>
					<Table.Head class="w-12 text-center">Pri</Table.Head>
					<Table.Head class="w-24">Owner</Table.Head>
					<Table.Head class="w-24">Created</Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each data.defects as defect, i}
					<Table.Row
						class="cursor-pointer {i === selectedIndex ? 'bg-muted' : ''}"
						data-index={i}
						onclick={() => goto(`/defects/${defect.id}`)}
					>
						<Table.Cell>
							<a href="/defects/{defect.id}" class="text-primary hover:underline text-sm" onclick={(e) => e.stopPropagation()}>
								#{defect.id}
							</a>
						</Table.Cell>
						<Table.Cell class="max-w-lg">
							<div class="flex items-center gap-2 flex-wrap">
								{#if defect.blocks && defect.blocks.length > 0}
									<Badge variant="destructive" class="text-xs px-1.5 py-0">
										Blocks {defect.blocks.join(', ')}
									</Badge>
								{/if}
								{#if defect.scenarios && defect.scenarios.length > 0}
									{#each defect.scenarios.slice(0, 3) as scenario}
										<Badge variant="secondary" class="text-xs px-1.5 py-0">{scenario}</Badge>
									{/each}
									{#if defect.scenarios.length > 3}
										<Badge variant="outline" class="text-xs px-1.5 py-0">+{defect.scenarios.length - 3}</Badge>
									{/if}
								{/if}
								{#if defect.integrations && defect.integrations.length > 0}
									{#each defect.integrations.slice(0, 2) as integration}
										<Badge variant="outline" class="text-xs px-1.5 py-0 text-blue-400">{integration}</Badge>
									{/each}
								{/if}
								<span class="truncate" title={defect.name}>{defect.clean_name || defect.name}</span>
							</div>
						</Table.Cell>
						<Table.Cell>
							<span class="text-xs text-muted-foreground">{defect.status || '-'}</span>
						</Table.Cell>
						<Table.Cell class="text-center">
							{@const p = getPriorityIndicator(defect.priority)}
							<span class="inline-flex items-center justify-center" title={defect.priority || 'No priority'}>
								<span class="w-2.5 h-2.5 rounded-full {p.color}"></span>
							</span>
						</Table.Cell>
						<Table.Cell class="truncate" title={defect.owner || ''}>{stripDomain(defect.owner)}</Table.Cell>
						<Table.Cell class="text-muted-foreground">{formatDate(defect.created)}</Table.Cell>
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>

	{/if}
</div>

<KeyboardShortcuts
	onNavigateDown={navigateDown}
	onNavigateUp={navigateUp}
	onSelect={selectCurrent}
	searchInput={searchInputEl}
/>
