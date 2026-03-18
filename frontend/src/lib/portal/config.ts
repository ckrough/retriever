import type { ModuleDefinition, ModuleStatus } from './types';
import { Layers, Clock } from '@lucide/svelte';
import { RETRIEVER_MODULE } from '$lib/modules/retriever/index';

export const MODULE_REGISTRY: ModuleDefinition[] = [
	RETRIEVER_MODULE,
	{
		id: 'heeler',
		name: 'Heeler',
		description: 'Automated document classification and tagging.',
		icon: Layers,
		basePath: '/app/heeler',
		status: 'locked',
		navItems: []
	},
	{
		id: 'drover',
		name: 'Drover',
		description: 'Scheduled document processing and workflow automation.',
		icon: Clock,
		basePath: '/app/drover',
		status: 'locked',
		navItems: []
	}
];

export function getActiveModule(pathname: string): ModuleDefinition | undefined {
	return MODULE_REGISTRY.find((m) => pathname.startsWith(m.basePath));
}

export function resolveModuleStatus(moduleId: string, subscriptions: Set<string>): ModuleStatus {
	return subscriptions.has(moduleId) ? 'active' : 'locked';
}

export function getModulesWithStatus(subscriptions: Set<string>): ModuleDefinition[] {
	return MODULE_REGISTRY.map((m) => ({
		...m,
		status: resolveModuleStatus(m.id, subscriptions)
	}));
}
