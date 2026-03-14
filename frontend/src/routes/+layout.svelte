<script lang="ts">
	import '../app.css';
	import { AppBar } from '@skeletonlabs/skeleton-svelte';
	import { invalidate } from '$app/navigation';
	import { onMount } from 'svelte';

	let { data, children } = $props();

	onMount(() => {
		const {
			data: { subscription }
		} = data.supabase.auth.onAuthStateChange(
			(event: string) => {
				if (event === 'SIGNED_OUT') {
					invalidate('supabase:auth');
				}
			}
		);

		return () => subscription.unsubscribe();
	});
</script>

<div class="flex h-screen flex-col" data-theme="cerberus">
	<AppBar>
		{#snippet lead()}
			<a href="/" class="text-xl font-bold">Retriever</a>
		{/snippet}
		{#snippet trail()}
			<nav class="flex items-center gap-4">
				{#if data.user}
					<a href="/chat" class="btn btn-sm preset-tonal">Chat</a>
					{#if data.user.app_metadata?.is_admin}
						<a href="/admin" class="btn btn-sm preset-tonal">Admin</a>
					{/if}
					<span class="text-sm text-surface-600-400">{data.user.email}</span>
					<form method="POST" action="/logout">
						<button type="submit" class="btn btn-sm preset-tonal-error">Sign Out</button>
					</form>
				{:else}
					<a href="/login" class="btn btn-sm preset-filled-primary-500">Sign In</a>
				{/if}
			</nav>
		{/snippet}
	</AppBar>
	<main class="flex-1 overflow-auto p-4">
		{@render children()}
	</main>
</div>
