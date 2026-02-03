<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fetchKanban } from '$lib/api';
	import type { KanbanResponse, KanbanDefect } from '$lib/types';
	import * as Select from '$lib/components/ui/select';
	import { onMount } from 'svelte';

	let data: KanbanResponse | null = $state(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// URL params
	let lane = $state<string>('');
	let includeHidden = $state(false);

	// Keyboard navigation state
	let focusedColumn = $state(0);
	let focusedRow = $state(0);
	let focusedLane = $state(0);

	// Group defects by status (and optionally by lane)
	let groupedDefects = $derived.by(() => {
		if (!data) return new Map<string, KanbanDefect[]>();

		const grouped = new Map<string, KanbanDefect[]>();
		for (const col of data.columns) {
			grouped.set(col, []);
		}

		for (const defect of data.defects) {
			const status = defect.status || 'Unknown';
			// Find matching column (case-insensitive)
			const col = data.columns.find((c) => c.toLowerCase() === status.toLowerCase()) || status;
			if (!grouped.has(col)) {
				grouped.set(col, []);
			}
			grouped.get(col)!.push(defect);
		}

		return grouped;
	});

	// Get defects for a specific column and lane
	function getDefectsForCell(column: string, laneValue?: string): KanbanDefect[] {
		const colDefects = groupedDefects.get(column) || [];
		if (!laneValue || !data?.lane_field) {
			return colDefects;
		}
		return colDefects.filter((d) => {
			const fieldValue = d[data!.lane_field as keyof KanbanDefect];
			return fieldValue === laneValue;
		});
	}

	// Get column counts
	function getColumnCount(column: string): number {
		return groupedDefects.get(column)?.length || 0;
	}

	// Priority color helper
	function getPriorityColor(priority: string | null): string {
		if (!priority) return 'bg-muted';
		if (priority.includes('1')) return 'bg-red-500';
		if (priority.includes('2')) return 'bg-orange-500';
		if (priority.includes('3')) return 'bg-yellow-500';
		if (priority.includes('4')) return 'bg-green-500';
		return 'bg-muted';
	}

	// Owner initials helper
	function getOwnerInitials(owner: string | null): string {
		if (!owner) return '?';
		// Handle email format like "john.doe_company.com"
		const name = owner.split('_')[0].split('@')[0];
		const parts = name.split('.');
		if (parts.length >= 2) {
			return (parts[0][0] + parts[1][0]).toUpperCase();
		}
		return name.slice(0, 2).toUpperCase();
	}

	// Load data
	async function loadData() {
		loading = true;
		error = null;
		try {
			data = await fetchKanban({
				lane: lane || undefined,
				include_hidden: includeHidden,
			});
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load kanban';
		} finally {
			loading = false;
		}
	}

	// Handle filter changes
	function handleLaneChange(value: string) {
		lane = value;
		updateUrl();
		loadData();
	}

	function handleHiddenToggle() {
		includeHidden = !includeHidden;
		updateUrl();
		loadData();
	}

	function updateUrl() {
		const params = new URLSearchParams();
		if (lane) params.set('lane', lane);
		if (includeHidden) params.set('include_hidden', 'true');
		const search = params.toString();
		goto(search ? `?${search}` : '/kanban', { replaceState: true, noScroll: true });
	}

	// Keyboard navigation
	function handleKeyDown(e: KeyboardEvent) {
		const target = e.target as HTMLElement;
		const isInputFocused =
			target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

		if (isInputFocused) return;
		if (!data) return;

		const columns = data.columns;
		const lanes = data.lanes.length > 0 ? data.lanes : [null];

		switch (e.key) {
			case 'ArrowRight':
				if (focusedColumn < columns.length - 1) {
					focusedColumn++;
					focusedRow = 0;
				}
				e.preventDefault();
				break;
			case 'ArrowLeft':
				if (focusedColumn > 0) {
					focusedColumn--;
					focusedRow = 0;
				}
				e.preventDefault();
				break;
			case 'ArrowDown':
			case 'j': {
				const currentCol = columns[focusedColumn];
				const currentLane = lanes[focusedLane];
				const defects = getDefectsForCell(currentCol, currentLane ?? undefined);
				if (focusedRow < defects.length - 1) {
					focusedRow++;
				} else if (focusedColumn < columns.length - 1) {
					// Wrap to next column
					focusedColumn++;
					focusedRow = 0;
				}
				e.preventDefault();
				break;
			}
			case 'ArrowUp':
			case 'k': {
				if (focusedRow > 0) {
					focusedRow--;
				} else if (focusedColumn > 0) {
					// Wrap to previous column
					focusedColumn--;
					const prevCol = columns[focusedColumn];
					const currentLane = lanes[focusedLane];
					const defects = getDefectsForCell(prevCol, currentLane ?? undefined);
					focusedRow = Math.max(0, defects.length - 1);
				}
				e.preventDefault();
				break;
			}
			case 'Enter': {
				const currentCol = columns[focusedColumn];
				const currentLane = lanes[focusedLane];
				const defects = getDefectsForCell(currentCol, currentLane ?? undefined);
				if (defects[focusedRow]) {
					goto(`/defects/${defects[focusedRow].id}`);
				}
				e.preventDefault();
				break;
			}
		}

		// Scroll focused card into view
		setTimeout(() => {
			const focused = document.querySelector('[data-focused="true"]');
			focused?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
		}, 0);
	}

	// Parse URL params on mount
	onMount(() => {
		const urlParams = new URLSearchParams($page.url.search);
		lane = urlParams.get('lane') || '';
		includeHidden = urlParams.get('include_hidden') === 'true';
		loadData();

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	});

	// Check if a card is focused
	function isFocused(colIndex: number, rowIndex: number, laneIndex: number = 0): boolean {
		return focusedColumn === colIndex && focusedRow === rowIndex && focusedLane === laneIndex;
	}
</script>

<svelte:head>
	<title>Kanban - ALM Defects</title>
</svelte:head>

<div class="h-screen flex flex-col">
	<!-- Header -->
	<div class="flex-none border-b bg-background px-4 py-3">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-4">
				<h1 class="text-xl font-semibold">Kanban Board</h1>
				{#if data}
					<span class="text-sm text-muted-foreground">
						{data.defects.length} defects
					</span>
				{/if}
			</div>
			<div class="flex items-center gap-4">
				<!-- Swimlane selector -->
				<Select.Root type="single" value={lane} onValueChange={handleLaneChange}>
					<Select.Trigger class="w-40">
						{#if lane === 'priority'}
							By Priority
						{:else if lane === 'owner'}
							By Owner
						{:else if lane === 'module'}
							By Module
						{:else if lane === 'workstream'}
							By Workstream
						{:else}
							No Swimlanes
						{/if}
					</Select.Trigger>
					<Select.Content>
						<Select.Item value="">No Swimlanes</Select.Item>
						<Select.Item value="priority">By Priority</Select.Item>
						<Select.Item value="owner">By Owner</Select.Item>
						<Select.Item value="module">By Module</Select.Item>
						<Select.Item value="workstream">By Workstream</Select.Item>
					</Select.Content>
				</Select.Root>

				<!-- Include hidden toggle -->
				<label class="flex items-center gap-2 text-sm">
					<input
						type="checkbox"
						checked={includeHidden}
						onchange={handleHiddenToggle}
						class="rounded border-input"
					/>
					Show hidden
				</label>
			</div>
		</div>
	</div>

	<!-- Board content -->
	{#if loading}
		<div class="flex-1 flex items-center justify-center text-muted-foreground">Loading...</div>
	{:else if error}
		<div class="flex-1 flex items-center justify-center text-destructive">{error}</div>
	{:else if data}
		<div class="flex-1 overflow-auto">
			{#if data.lanes.length > 0}
				<!-- With swimlanes - CSS Grid layout -->
				{@const gridCols = `12rem repeat(${data.columns.length}, 16rem)`}
				<div
					class="grid min-w-max"
					style="grid-template-columns: {gridCols};"
				>
					<!-- Header row -->
					<div class="sticky top-0 left-0 z-30 bg-background border-b border-r px-3 py-2">
						<!-- Empty corner cell -->
					</div>
					{#each data.columns as column, colIndex}
						<div
							class="sticky top-0 z-20 bg-background border-b border-r px-3 py-2"
						>
							<div class="font-medium">{column}</div>
							<div class="text-xs text-muted-foreground">{getColumnCount(column)}</div>
						</div>
					{/each}

					<!-- Swimlane rows -->
					{#each data.lanes as laneValue, laneIndex}
						<!-- Lane header cell -->
						<div class="sticky left-0 z-10 bg-muted/50 border-b border-r px-3 py-2 font-medium truncate" title={laneValue}>
							{laneValue}
						</div>
						<!-- Lane content cells -->
						{#each data.columns as column, colIndex}
							{@const defects = getDefectsForCell(column, laneValue)}
							<div class="border-b border-r p-2 min-h-[100px] bg-background">
								<div class="space-y-2">
									{#each defects as defect, rowIndex}
										<a
											href="/defects/{defect.id}"
											class="block p-2 bg-card border rounded shadow-sm hover:shadow-md transition-shadow {isFocused(
												colIndex,
												rowIndex,
												laneIndex
											)
												? 'ring-2 ring-primary'
												: ''}"
											data-focused={isFocused(colIndex, rowIndex, laneIndex)}
										>
											<div class="flex items-start justify-between gap-2">
												<span class="text-xs text-muted-foreground">#{defect.id}</span>
												<span
													class="w-2 h-2 rounded-full flex-none {getPriorityColor(
														defect.priority
													)}"
													title={defect.priority || 'No priority'}
												></span>
											</div>
											<div class="text-sm line-clamp-2 mt-1">{defect.name}</div>
											<div class="flex items-center justify-between mt-2">
												<span
													class="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs"
													title={defect.owner || 'Unassigned'}
												>
													{getOwnerInitials(defect.owner)}
												</span>
											</div>
										</a>
									{/each}
								</div>
							</div>
						{/each}
					{/each}
				</div>
			{:else}
				<!-- Without swimlanes -->
				<div class="flex min-w-max h-full">
					{#each data.columns as column, colIndex}
						{@const defects = getDefectsForCell(column)}
						<div
							class="w-64 flex-none flex flex-col border-r {colIndex === 0
								? 'sticky left-0 z-20 bg-background'
								: ''}"
						>
							<!-- Column header -->
							<div class="sticky top-0 bg-background border-b px-3 py-2 {colIndex === 0 ? 'z-30' : 'z-10'}">
								<div class="font-medium">{column}</div>
								<div class="text-xs text-muted-foreground">{defects.length} defects</div>
							</div>
							<!-- Cards -->
							<div class="flex-1 overflow-y-auto p-2 space-y-2">
								{#each defects as defect, rowIndex}
									<a
										href="/defects/{defect.id}"
										class="block p-2 bg-card border rounded shadow-sm hover:shadow-md transition-shadow {isFocused(
											colIndex,
											rowIndex
										)
											? 'ring-2 ring-primary'
											: ''}"
										data-focused={isFocused(colIndex, rowIndex)}
									>
										<div class="flex items-start justify-between gap-2">
											<span class="text-xs text-muted-foreground">#{defect.id}</span>
											<span
												class="w-2 h-2 rounded-full flex-none {getPriorityColor(defect.priority)}"
												title={defect.priority || 'No priority'}
											></span>
										</div>
										<div class="text-sm line-clamp-2 mt-1">{defect.name}</div>
										<div class="flex items-center justify-between mt-2">
											<span
												class="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs"
												title={defect.owner || 'Unassigned'}
											>
												{getOwnerInitials(defect.owner)}
											</span>
										</div>
									</a>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Keyboard hint -->
<div
	class="fixed bottom-4 left-4 text-xs text-muted-foreground bg-background/90 backdrop-blur-sm px-2 py-1 rounded border"
>
	<kbd class="font-mono bg-muted px-1 py-0.5 rounded">Arrow keys</kbd> navigate
	<kbd class="font-mono bg-muted px-1 py-0.5 rounded ml-2">Enter</kbd> open
</div>
