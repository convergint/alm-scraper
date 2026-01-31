<script lang="ts">
	import { fetchDefects, type DefectsParams } from '$lib/api';
	import type { Defect, DefectsResponse } from '$lib/types';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Input } from '$lib/components/ui/input';
	import * as Table from '$lib/components/ui/table';
	import * as Select from '$lib/components/ui/select';

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
	<form onsubmit={handleSearch} class="mb-6 flex flex-wrap gap-4 items-end">
		<div class="flex-1 min-w-48">
			<Input
				type="text"
				bind:value={search}
				placeholder="Search defects..."
			/>
		</div>

		<Select.Root type="single" bind:value={status} onValueChange={handleFilterChange}>
			<Select.Trigger class="w-40">
				{status ? (status === 'open' ? 'Open' : status === 'closed' ? 'Closed' : 'Rejected') : 'All Status'}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="">All Status</Select.Item>
				<Select.Item value="open">Open</Select.Item>
				<Select.Item value="closed">Closed</Select.Item>
				<Select.Item value="rejected">Rejected</Select.Item>
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

		<Button type="submit">Search</Button>
	</form>

	<!-- Loading / Error states -->
	{#if loading}
		<div class="text-center py-12 text-muted-foreground">Loading...</div>
	{:else if error}
		<div class="text-center py-12 text-destructive">{error}</div>
	{:else if data}
		<!-- Results count -->
		<div class="mb-4 text-muted-foreground">
			Showing {data.defects.length} of {data.total} defects (page {data.page} of {data.pages})
		</div>

		<!-- Defects table -->
		<Table.Root>
			<Table.Header>
				<Table.Row>
					<Table.Head class="w-16">ID</Table.Head>
					<Table.Head>Name</Table.Head>
					<Table.Head class="w-12 text-center">Pri</Table.Head>
					<Table.Head class="w-24">Owner</Table.Head>
					<Table.Head class="w-24">Created</Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each data.defects as defect}
					<Table.Row class="cursor-pointer" onclick={() => goto(`/defects/${defect.id}`)}>
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

		<!-- Pagination -->
		{#if data.pages > 1}
			<div class="mt-6 flex justify-center gap-2 items-center">
				<Button
					variant="outline"
					onclick={() => goToPage(currentPage - 1)}
					disabled={currentPage === 1}
				>
					Previous
				</Button>
				<span class="px-4 text-muted-foreground">
					Page {currentPage} of {data.pages}
				</span>
				<Button
					variant="outline"
					onclick={() => goToPage(currentPage + 1)}
					disabled={currentPage === data.pages}
				>
					Next
				</Button>
			</div>
		{/if}
	{/if}
</div>
