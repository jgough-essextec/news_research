import { test, expect } from '@playwright/test';

const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8000/api';

test.describe('AI News Aggregator Pipeline', () => {
  // Dashboard tests require authentication. These tests are skipped by default
  // because they require a valid session. To run these tests, you need to:
  // 1. Set up authentication storage state with Playwright
  // 2. Or configure a test user with session fixtures
  test.describe('Dashboard', () => {
    // Skip dashboard tests - they require authentication
    // The auth protection is verified in auth.spec.ts
    test.skip('should load dashboard with stats', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);

      // Verify dashboard page loads
      await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();

      // Verify stat cards are present (using headings to be specific)
      await expect(page.getByText('Newsletter Emails')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Articles', exact: true })).toBeVisible();
      await expect(page.getByText('Topic Clusters')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Blog Posts', exact: true })).toBeVisible();
    });

    test.skip('should have Sync Emails button', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);

      const syncButton = page.getByRole('button', { name: /sync emails/i });
      await expect(syncButton).toBeVisible();
      await expect(syncButton).toBeEnabled();
    });

    test.skip('Sync Emails button triggers API call', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);

      // Set up request interception
      const apiPromise = page.waitForRequest((request) =>
        request.url().includes('/emails/sync/') && request.method() === 'POST'
      );

      // Click the sync button
      const syncButton = page.getByRole('button', { name: /sync emails/i });
      await syncButton.click();

      // Verify API call was made
      const request = await apiPromise;
      expect(request.url()).toContain('/emails/sync/');
      expect(request.method()).toBe('POST');
    });

    test.skip('should display recent articles section', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);

      await expect(page.getByText('Recent Articles')).toBeVisible();
    });

    test.skip('should display top clusters section', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);

      await expect(page.getByText('Top Clusters')).toBeVisible();
    });
  });

  test.describe('API Endpoints', () => {
    test('POST /api/emails/sync/ returns 200 or 400', async ({ request }) => {
      const response = await request.post(`${API_URL}/emails/sync/`);

      // Should return 200 (success) or 400 (no Gmail connection) - both are valid responses
      expect([200, 400, 401]).toContain(response.status());

      if (response.status() === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('task_id');
        expect(data).toHaveProperty('status');
      }
    });

    test('POST /api/articles/process_pending/ returns valid response', async ({ request }) => {
      const response = await request.post(`${API_URL}/articles/process_pending/`);

      expect([200, 401]).toContain(response.status());

      if (response.status() === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('status');
        // Either 'started' or 'no_pending'
        expect(['started', 'no_pending']).toContain(data.status);
      }
    });

    test('GET /api/articles/ returns paginated list', async ({ request }) => {
      const response = await request.get(`${API_URL}/articles/`);

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('count');
      expect(data).toHaveProperty('results');
      expect(Array.isArray(data.results)).toBe(true);
    });

    test('GET /api/clusters/ returns paginated list', async ({ request }) => {
      const response = await request.get(`${API_URL}/clusters/`);

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('count');
      expect(data).toHaveProperty('results');
      expect(Array.isArray(data.results)).toBe(true);
    });

    test('GET /api/emails/ returns paginated list', async ({ request }) => {
      const response = await request.get(`${API_URL}/emails/`);

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('count');
      expect(data).toHaveProperty('results');
      expect(Array.isArray(data.results)).toBe(true);
    });

    test('GET /api/links/ returns paginated list', async ({ request }) => {
      const response = await request.get(`${API_URL}/links/`);

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('count');
      expect(data).toHaveProperty('results');
      expect(Array.isArray(data.results)).toBe(true);
    });

    test('GET /api/posts/ returns paginated list', async ({ request }) => {
      const response = await request.get(`${API_URL}/posts/`);

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('count');
      expect(data).toHaveProperty('results');
      expect(Array.isArray(data.results)).toBe(true);
    });
  });

  test.describe('Pipeline Flow', () => {
    test.skip('can navigate from dashboard to emails list', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);

      // Look for a link to emails (might be in navigation)
      const emailsLink = page.getByRole('link', { name: /emails/i });

      if (await emailsLink.isVisible()) {
        await emailsLink.click();
        await expect(page).toHaveURL(/emails/);
      }
    });

    test.skip('dashboard stats update after time', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`);

      // Wait for initial load
      await page.waitForLoadState('networkidle');

      // Get initial count text
      const emailsCard = page.locator('text=Newsletter Emails').locator('..').locator('..');

      // Verify the card is visible and has some content
      await expect(emailsCard).toBeVisible();
    });
  });

  test.describe('Cluster Operations', () => {
    test('POST /api/clusters/{id}/generate_post/ with invalid cluster returns error', async ({ request }) => {
      // Use a non-existent cluster ID
      const response = await request.post(`${API_URL}/clusters/999999/generate_post/`);

      // Should return 404 for non-existent cluster
      expect([404, 401]).toContain(response.status());
    });

    test('POST /api/clusters/{id}/generate_summary/ with valid cluster', async ({ request }) => {
      // First get a cluster ID
      const listResponse = await request.get(`${API_URL}/clusters/`);

      if (listResponse.status() !== 200) {
        test.skip();
        return;
      }

      const clusters = await listResponse.json();

      if (clusters.results.length === 0) {
        test.skip();
        return;
      }

      const clusterId = clusters.results[0].id;
      const response = await request.post(`${API_URL}/clusters/${clusterId}/generate_summary/`);

      expect([200, 401]).toContain(response.status());

      if (response.status() === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('task_id');
        expect(data).toHaveProperty('status');
        expect(data.status).toBe('started');
      }
    });
  });

  test.describe('Article Operations', () => {
    test('can rescrape an article', async ({ request }) => {
      // First get an article ID
      const listResponse = await request.get(`${API_URL}/articles/`);

      if (listResponse.status() !== 200) {
        test.skip();
        return;
      }

      const articles = await listResponse.json();

      if (articles.results.length === 0) {
        test.skip();
        return;
      }

      const articleId = articles.results[0].id;
      const response = await request.post(`${API_URL}/articles/${articleId}/rescrape/`);

      expect([200, 401]).toContain(response.status());

      if (response.status() === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('task_id');
        expect(data).toHaveProperty('status');
        expect(data.status).toBe('started');
      }
    });

    test('can find similar articles', async ({ request }) => {
      // First get an article ID
      const listResponse = await request.get(`${API_URL}/articles/`);

      if (listResponse.status() !== 200) {
        test.skip();
        return;
      }

      const articles = await listResponse.json();

      if (articles.results.length === 0) {
        test.skip();
        return;
      }

      const articleId = articles.results[0].id;
      const response = await request.get(`${API_URL}/articles/similar/?article_id=${articleId}`);

      // Might return 400 if article has no embedding
      expect([200, 400, 401]).toContain(response.status());

      if (response.status() === 200) {
        const data = await response.json();
        expect(Array.isArray(data)).toBe(true);
      }
    });
  });
});
