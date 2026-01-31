<script lang="ts">
	import { fetchDefect } from '$lib/api';
	import type { Defect } from '$lib/types';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as Card from '$lib/components/ui/card';
	import { Separator } from '$lib/components/ui/separator';

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
			<h1 class="text-2xl font-bold mb-4">{defect.name}</h1>

			<div class="flex flex-wrap gap-2">
				<Badge variant={defect.status === 'Open' ? 'default' : 'secondary'}>
					{defect.status || 'Unknown'}
				</Badge>
				<Badge variant={getPriorityVariant(defect.priority)}>
					{defect.priority || 'No priority'}
				</Badge>
			</div>
		</div>

		<!-- Metadata grid -->
		<Card.Root class="mb-8">
			<Card.Content class="pt-6">
				<div class="grid grid-cols-2 md:grid-cols-3 gap-4">
					<div>
						<div class="text-muted-foreground text-sm">Owner</div>
						<div>{stripDomain(defect.owner)}</div>
					</div>
					<div>
						<div class="text-muted-foreground text-sm">Detected By</div>
						<div>{stripDomain(defect.detected_by)}</div>
					</div>
					<div>
						<div class="text-muted-foreground text-sm">Severity</div>
						<div>{defect.severity || '-'}</div>
					</div>
					<div>
						<div class="text-muted-foreground text-sm">Type</div>
						<div>{defect.defect_type || '-'}</div>
					</div>
					<div>
						<div class="text-muted-foreground text-sm">Module</div>
						<div>{defect.module || '-'}</div>
					</div>
					<div>
						<div class="text-muted-foreground text-sm">Workstream</div>
						<div>{defect.workstream || '-'}</div>
					</div>
					<div>
						<div class="text-muted-foreground text-sm">Created</div>
						<div>{formatDate(defect.created)}</div>
					</div>
					<div>
						<div class="text-muted-foreground text-sm">Modified</div>
						<div>{formatDate(defect.modified)}</div>
					</div>
					<div>
						<div class="text-muted-foreground text-sm">Closed</div>
						<div>{formatDate(defect.closed)}</div>
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
