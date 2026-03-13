<script lang="ts">
	import '../app.css';
	import { AppBar } from '@skeletonlabs/skeleton-svelte';

	let { children } = $props();
</script>

<div class="h-screen flex flex-col" data-theme="cerberus">
	<AppBar>
		{#snippet lead()}
			<h1 class="text-xl font-bold">Retriever</h1>
		{/snippet}
	</AppBar>
	<main class="flex-1 overflow-auto p-4">
		{@render children()}
	</main>
</div>
