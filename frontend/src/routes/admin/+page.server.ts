import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	if (!locals.user) {
		redirect(303, '/login');
	}

	if (!locals.user.app_metadata?.is_admin) {
		redirect(303, '/chat');
	}
};
