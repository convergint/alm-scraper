<script lang="ts">
	import { fetchDefect } from '$lib/api';
	import type { Defect } from '$lib/types';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as Card from '$lib/components/ui/card';
	import { Separator } from '$lib/components/ui/separator';
	import KeyboardShortcuts from '$lib/components/KeyboardShortcuts.svelte';

	let defect: Defect | null = $state(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		const d = new Date(dateStr);
		return d.toISOString().replace('T', ' ').slice(0, 19);
	}

	function stripDomain(owner: string | null): string {
		if (!owner) return '-';
		return owner.includes('_') ? owner.split('_')[0] : owner;
	}

	function getPriorityVariant(priority: string | null): 'destructive' | 'secondary' | 'outline' {
		if (!priority) return 'outline';
		if (priority.includes('1')) return 'destructive';
		if (priority.includes('2')) return 'secondary';
		return 'outline';
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
	<Button variant="ghost" href="/" class="mb-6">
		&larr; Back to list
	</Button>

	{#if loading}
		<div class="text-center py-12 text-muted-foreground">Loading...</div>
	{:else if error}
		<div class="text-center py-12 text-destructive">{error}</div>
	{:else if defect}
		<!-- Header -->
		<div class="mb-8">
			<div class="text-muted-foreground mb-2">#{defect.id}</div>
			<h1 class="text-2xl font-bold mb-4">{defect.clean_name || defect.name}</h1>

			<div class="flex flex-wrap gap-2 mb-3">
				<Badge variant={defect.status === 'Open' ? 'default' : 'secondary'}>
					{defect.status || 'Unknown'}
				</Badge>
				<Badge variant={getPriorityVariant(defect.priority)}>
					{defect.priority || 'No priority'}
				</Badge>
			</div>

			<!-- Scenario codes -->
			{#if (defect.scenarios && defect.scenarios.length > 0) || (defect.blocks && defect.blocks.length > 0) || (defect.integrations && defect.integrations.length > 0)}
				<div class="flex flex-wrap gap-2">
					{#if defect.blocks && defect.blocks.length > 0}
						<Badge variant="destructive">
							Blocks: {defect.blocks.join(', ')}
						</Badge>
					{/if}
					{#if defect.scenarios && defect.scenarios.length > 0}
						{#each defect.scenarios as scenario}
							<Badge variant="secondary">{scenario}</Badge>
						{/each}
					{/if}
					{#if defect.integrations && defect.integrations.length > 0}
						{#each defect.integrations as integration}
							<Badge variant="outline" class="text-blue-400">{integration}</Badge>
						{/each}
					{/if}
				</div>
			{/if}
		</div>

		<!-- Metadata -->
		<Card.Root class="mb-8">
			<Card.Content class="py-5 px-6">
				<!-- Classification row - top -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-1 text-sm mb-5 pb-5 border-b border-border">
					<div>
						<span class="text-muted-foreground">Type:</span>
						<span class="ml-1.5">{defect.defect_type || '-'}</span>
					</div>
					<div>
						<span class="text-muted-foreground">Module:</span>
						<span class="ml-1.5">{defect.module || '-'}</span>
					</div>
					<div>
						<span class="text-muted-foreground">Workstream:</span>
						<span class="ml-1.5">{defect.workstream || '-'}</span>
					</div>
					<div>
						<span class="text-muted-foreground">Severity:</span>
						<span class="ml-1.5">{defect.severity || '-'}</span>
					</div>
				</div>

				<!-- Main info row -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-4">
					<div>
						<div class="text-xs uppercase tracking-wide text-muted-foreground mb-1">Owner</div>
						<div class="text-base font-medium">{stripDomain(defect.owner)}</div>
					</div>
					<div>
						<div class="text-xs uppercase tracking-wide text-muted-foreground mb-1">Detected By</div>
						<div class="text-base">{stripDomain(defect.detected_by)}</div>
					</div>
					<div>
						<div class="text-xs uppercase tracking-wide text-muted-foreground mb-1">Created</div>
						<div class="text-base">{formatDate(defect.created).split(' ')[0]}</div>
					</div>
					<div>
						<div class="text-xs uppercase tracking-wide text-muted-foreground mb-1">Modified</div>
						<div class="text-base">{formatDate(defect.modified).split(' ')[0]}</div>
					</div>
				</div>
			</Card.Content>
		</Card.Root>

		<!-- Description -->
		{#if defect.description}
			<Card.Root class="mb-8">
				<Card.Header>
					<Card.Title>Description</Card.Title>
				</Card.Header>
				<Card.Content class="html-content">
					{@html defect.description}
				</Card.Content>
			</Card.Root>
		{/if}

		<!-- Dev Comments -->
		{#if defect.dev_comments}
			<Card.Root class="mb-8">
				<Card.Header>
					<Card.Title>Dev Comments</Card.Title>
				</Card.Header>
				<Card.Content class="html-content">
					{@html defect.dev_comments}
				</Card.Content>
			</Card.Root>
		{/if}

		<!-- Additional details -->
		<Separator class="my-6" />
		<div class="text-sm text-muted-foreground">
			<p>Press <kbd class="px-2 py-1 bg-muted rounded">Esc</kbd> to return to list</p>
		</div>
	{/if}
</div>

<KeyboardShortcuts />
