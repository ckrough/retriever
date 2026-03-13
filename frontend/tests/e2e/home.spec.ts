import { test, expect } from '@playwright/test';

test.describe('Home page', () => {
	test('renders app bar with title', async ({ page }) => {
		await page.goto('/');
		await expect(page.getByRole('heading', { name: 'Retriever', exact: true })).toBeVisible();
	});

	test('renders page heading and tagline', async ({ page }) => {
		await page.goto('/');
		await expect(page.getByRole('heading', { name: 'Ask Retriever' })).toBeVisible();
		await expect(page.getByText('AI-powered Q&A for shelter volunteers')).toBeVisible();
	});

	test('screenshot', async ({ page }) => {
		await page.goto('/');
		await expect(page).toHaveScreenshot('home.png');
	});
});
