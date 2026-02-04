<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	// Props for page-specific behavior
	interface Props {
		onNavigateDown?: () => void;
		onNavigateUp?: () => void;
		onSelect?: () => void;
		searchInput?: HTMLInputElement | null;
	}

	let { onNavigateDown, onNavigateUp, onSelect, searchInput }: Props = $props();

	// State for chord sequences
	let pendingChord = $state('');
	let chordTimeout: ReturnType<typeof setTimeout> | null = null;
	let showGoToDefect = $state(false);
	let goToDefectId = $state('');
	let goToDefectInput: HTMLInputElement | null = $state(null);
	let goToDefectContainer: HTMLDivElement | null = $state(null);
	let showHelp = $state(false);
	let toastMessage = $state('');
	let toastTimeout: ReturnType<typeof setTimeout> | null = null;

	function showToast(message: string, duration = 2000) {
		toastMessage = message;
		if (toastTimeout) clearTimeout(toastTimeout);
		toastTimeout = setTimeout(() => {
			toastMessage = '';
		}, duration);
	}

	function clearChord() {
		pendingChord = '';
		if (chordTimeout) {
			clearTimeout(chordTimeout);
			chordTimeout = null;
		}
	}

	function startChord(key: string) {
		pendingChord = key;
		showToast(`${key} ...`, 1500);
		chordTimeout = setTimeout(clearChord, 1500);
	}

	async function validateAndGoToDefect(id: string) {
		const numId = parseInt(id, 10);
		if (isNaN(numId) || numId <= 0) {
			showToast(`Invalid defect ID: ${id}`);
			return;
		}

		try {
			const res = await fetch(`/api/defects/${numId}`);
			if (res.ok) {
				goto(`/defects/${numId}`);
			} else {
				showToast(`Defect #${numId} not found`);
			}
		} catch {
			showToast(`Error checking defect #${numId}`);
		}
	}

	function closeGoToDefect() {
		showGoToDefect = false;
		goToDefectId = '';
	}

	function handleGoToDefectKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			if (goToDefectId) validateAndGoToDefect(goToDefectId);
			closeGoToDefect();
			e.preventDefault();
		} else if (e.key === 'Escape') {
			closeGoToDefect();
			e.preventDefault();
		} else if (
			// Allow: digits, backspace, delete, arrows, tab, home, end
			!/^\d$/.test(e.key) &&
			!['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab', 'Home', 'End'].includes(e.key) &&
			// Allow Ctrl/Cmd shortcuts (paste, select all, etc.)
			!e.ctrlKey && !e.metaKey
		) {
			e.preventDefault();
		}
	}

	function handleGoToDefectInput(e: Event) {
		const input = e.target as HTMLInputElement;
		// Filter to digits only
		goToDefectId = input.value.replace(/\D/g, '');
	}

	function handleGoToDefectClickOutside(e: MouseEvent) {
		if (goToDefectContainer && !goToDefectContainer.contains(e.target as Node)) {
			closeGoToDefect();
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		const target = e.target as HTMLElement;
		const isInputFocused = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

		// Go-to-defect input handles its own keyboard events
		if (showGoToDefect) {
			return;
		}

		// Handle help overlay
		if (showHelp) {
			if (e.key === 'Escape' || e.key === '?') {
				showHelp = false;
				e.preventDefault();
				return;
			}
			return;
		}

		// Don't handle shortcuts when input is focused (except Escape)
		if (isInputFocused) {
			if (e.key === 'Escape') {
				(target as HTMLElement).blur();
				e.preventDefault();
			}
			return;
		}

		// Handle chord sequences
		if (pendingChord === 'g') {
			clearChord();
			toastMessage = ''; // Clear the "g ..." toast

			if (e.key === 'd') {
				showGoToDefect = true;
				goToDefectId = '';
				e.preventDefault();
				return;
			}
			if (e.key === 'h') {
				goto('/');
				e.preventDefault();
				return;
			}
			if (e.key === 's') {
				goto('/stats');
				e.preventDefault();
				return;
			}
			if (e.key === 'b') {
				goto('/kanban');
				e.preventDefault();
				return;
			}
			// Invalid chord, ignore
			return;
		}

		// Start new chord or single-key shortcuts
		switch (e.key) {
			case 'g':
				startChord('g');
				e.preventDefault();
				break;
			case '/':
				searchInput?.focus();
				e.preventDefault();
				break;
			case '?':
				showHelp = true;
				e.preventDefault();
				break;
			case 'j':
				onNavigateDown?.();
				e.preventDefault();
				break;
			case 'k':
				onNavigateUp?.();
				e.preventDefault();
				break;
			case 'Enter':
				onSelect?.();
				e.preventDefault();
				break;
			case 'Escape':
				clearChord();
				break;
		}
	}

	onMount(() => {
		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	});

	// Auto-focus input and handle click-outside when go-to-defect prompt opens
	$effect(() => {
		if (showGoToDefect) {
			// Focus the input after it's rendered
			setTimeout(() => goToDefectInput?.focus(), 0);
			// Add click-outside listener
			document.addEventListener('mousedown', handleGoToDefectClickOutside);
			return () => {
				document.removeEventListener('mousedown', handleGoToDefectClickOutside);
			};
		}
	});
</script>

<!-- Toast for chord feedback -->
{#if toastMessage}
	<div class="fixed bottom-16 left-4 bg-muted border rounded px-3 py-1.5 text-sm font-mono shadow-lg z-50">
		{toastMessage}
	</div>
{/if}

<!-- Go to defect input -->
{#if showGoToDefect}
	<div
		bind:this={goToDefectContainer}
		class="fixed bottom-16 left-4 bg-background border rounded px-3 py-2 shadow-lg z-50 flex items-center gap-2"
	>
		<label for="goto-defect-input" class="text-sm text-muted-foreground">Go to defect:</label>
		<input
			bind:this={goToDefectInput}
			id="goto-defect-input"
			type="text"
			inputmode="numeric"
			pattern="[0-9]*"
			value={goToDefectId}
			onkeydown={handleGoToDefectKeydown}
			oninput={handleGoToDefectInput}
			class="w-24 bg-transparent border-b border-primary font-mono text-primary focus:outline-none"
		/>
		<span class="text-xs text-muted-foreground ml-2">Enter to go, Esc to cancel</span>
	</div>
{/if}

<!-- Help overlay -->
{#if showHelp}
	<div
		class="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center"
		onclick={() => showHelp = false}
		onkeydown={(e) => e.key === 'Escape' && (showHelp = false)}
		role="button"
		tabindex="-1"
	>
		<div class="bg-card border rounded-lg shadow-xl p-6 max-w-md" onclick={(e) => e.stopPropagation()} role="presentation">
			<h2 class="text-lg font-semibold mb-4">Keyboard Shortcuts</h2>
			<div class="space-y-3 text-sm">
				<div class="grid grid-cols-[80px_1fr] gap-2">
					<h3 class="font-medium text-muted-foreground col-span-2 mt-2">Navigation</h3>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">j</kbd>
					<span>Move down</span>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">k</kbd>
					<span>Move up</span>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">Enter</kbd>
					<span>Open selected defect</span>

					<h3 class="font-medium text-muted-foreground col-span-2 mt-4">Go to</h3>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">g d</kbd>
					<span>Go to defect by ID</span>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">g h</kbd>
					<span>Go home (defect list)</span>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">g s</kbd>
					<span>Go to stats/dashboard</span>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">g b</kbd>
					<span>Go to kanban board</span>

					<h3 class="font-medium text-muted-foreground col-span-2 mt-4">Other</h3>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">/</kbd>
					<span>Focus search</span>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">?</kbd>
					<span>Show this help</span>
					<kbd class="font-mono bg-muted px-1.5 py-0.5 rounded text-xs">Esc</kbd>
					<span>Clear / close</span>
				</div>
			</div>
			<div class="mt-6 text-xs text-muted-foreground text-center">
				Press <kbd class="font-mono bg-muted px-1 py-0.5 rounded">Esc</kbd> or click outside to close
			</div>
		</div>
	</div>
{/if}

<!-- Footer hint -->
<div class="fixed bottom-4 left-4 text-xs text-muted-foreground bg-background/90 backdrop-blur-sm px-2 py-1 rounded border">
	Press <kbd class="font-mono bg-muted px-1 py-0.5 rounded">?</kbd> for keyboard shortcuts
</div>
