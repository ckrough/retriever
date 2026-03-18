<script lang="ts">
	import { LogOut } from '@lucide/svelte';

	interface Props {
		user: { email: string; role?: string } | null;
		compact: boolean;
	}

	let { user, compact }: Props = $props();

	let open = $state(false);

	let initials = $derived.by(() => {
		if (!user?.email) return '?';
		const parts = user.email.split('@')[0].split(/[._-]/);
		if (parts.length >= 2) {
			return (parts[0][0] + parts[1][0]).toUpperCase();
		}
		return user.email.substring(0, 2).toUpperCase();
	});

	function handleClickOutside(event: MouseEvent): void {
		const target = event.target as HTMLElement;
		if (!target.closest('.user-menu')) {
			open = false;
		}
	}

	function handleKeydown(event: KeyboardEvent): void {
		if (event.key === 'Escape') {
			open = false;
		}
	}

	$effect(() => {
		if (open) {
			document.addEventListener('click', handleClickOutside, true);
			return () => {
				document.removeEventListener('click', handleClickOutside, true);
			};
		}
	});
</script>

<svelte:window onkeydown={open ? handleKeydown : undefined} />

<div class="user-menu relative">
	<button
		type="button"
		class="flex min-h-[44px] min-w-[44px] items-center gap-2 rounded-lg px-2 transition-colors hover:bg-[var(--portal-hover-bg)]"
		onclick={() => (open = !open)}
		aria-expanded={open}
		aria-haspopup="menu"
		aria-label="User menu"
	>
		<span
			class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary-500)] text-xs font-semibold text-white"
		>
			{initials}
		</span>
		{#if !compact && user}
			<span class="hidden truncate text-sm text-[var(--portal-sidebar-text)] lg:block">
				{user.email}
			</span>
		{/if}
	</button>

	{#if open}
		<div
			class="absolute bottom-full right-0 z-50 mb-2 w-64 overflow-hidden rounded-xl border border-[var(--portal-border-color)] bg-[var(--portal-card-bg)] shadow-lg"
			role="menu"
		>
			{#if user}
				<div class="border-b border-[var(--portal-border-color)] px-4 py-3">
					<p class="truncate text-sm font-medium">{user.email}</p>
					{#if user.role}
						<span
							class="mt-1 inline-block rounded-full bg-[var(--color-primary-500)]/10 px-2 py-0.5 text-xs font-medium text-[var(--color-primary-500)]"
						>
							{user.role}
						</span>
					{/if}
				</div>
			{/if}
			<form method="POST" action="/logout">
				<button
					type="submit"
					class="flex min-h-[44px] w-full items-center gap-3 px-4 py-2 text-sm transition-colors hover:bg-[var(--portal-hover-bg)]"
					role="menuitem"
				>
					<LogOut size={16} class="opacity-60" />
					Sign out
				</button>
			</form>
		</div>
	{/if}
</div>
