<script lang="ts">
	import '../app.css';
	import NavBar from '$lib/components/NavBar.svelte';

	let { children } = $props();
</script>

<div class="dark min-h-screen bg-background text-foreground">
	<NavBar />
	{@render children()}
</div>
