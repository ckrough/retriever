<script lang="ts">
	interface Props {
		role: 'user' | 'assistant';
		content: string;
		createdAt?: string;
	}

	let { role, content, createdAt }: Props = $props();

	const initials = $derived(role === 'user' ? 'U' : 'R');
	const alignment = $derived(role === 'user' ? 'justify-end' : 'justify-start');
	const bubbleBg = $derived(
		role === 'user' ? 'preset-filled-primary-500' : 'preset-filled-surface-200-800'
	);
	const timeStr = $derived(createdAt ? new Date(createdAt).toLocaleTimeString() : '');
</script>

<div class="flex gap-3 {alignment}">
	{#if role === 'assistant'}
		<div
			class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-tertiary-500 text-sm font-bold"
		>
			{initials}
		</div>
	{/if}

	<div class="max-w-[75%] space-y-1">
		<div class="rounded-lg p-3 {bubbleBg}">
			<p class="whitespace-pre-wrap">{content}</p>
		</div>
		{#if timeStr}
			<p class="text-xs text-surface-500">{timeStr}</p>
		{/if}
	</div>

	{#if role === 'user'}
		<div
			class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-sm font-bold"
		>
			{initials}
		</div>
	{/if}
</div>
