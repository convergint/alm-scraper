<script lang="ts">
	import { page } from '$app/stores';

	// Determine active page from current path
	let currentPath = $derived($page.url.pathname);

	function isActive(path: string): boolean {
		if (path === '/') {
			return currentPath === '/';
		}
		return currentPath.startsWith(path);
	}
</script>

<nav class="border-b bg-background">
	<div class="container mx-auto px-4">
		<div class="flex items-center justify-between h-12">
			<div class="flex items-center gap-1">
				<a
					href="/"
					class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {isActive('/')
						? 'bg-muted text-foreground'
						: 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}"
				>
					List
				</a>
				<a
					href="/kanban"
					class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {isActive('/kanban')
						? 'bg-muted text-foreground'
						: 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}"
				>
					Kanban
				</a>
				<a
					href="/stats"
					class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {isActive('/stats')
						? 'bg-muted text-foreground'
						: 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}"
				>
					Dashboard
				</a>
			</div>
			<div class="text-sm text-muted-foreground">
				ALM Defects
			</div>
		</div>
	</div>
</nav>
