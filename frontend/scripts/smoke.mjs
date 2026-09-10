import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';

const url = process.argv[2] || 'http://127.0.0.1:8001/';
const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined });
const page = await browser.newPage({ viewport: { width: 1440, height: 1024 } });
const errors = [], failedAssets = [];
page.on('pageerror', error => errors.push(error.message));
page.on('response', response => { if (response.status() >= 400) failedAssets.push({ url: response.url(), status: response.status() }); });
try {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.getByRole('heading', { name: 'From signals to understanding.' }).waitFor();
  const bootstrap = await (await page.request.get(new URL('/api/bootstrap', url).href)).json();
  await page.getByRole('navigation').getByRole('button', { name: /Workflows/ }).click();
  await page.locator('.workflow-nodes .node').first().waitFor();
  const nodes = await page.locator('.workflow-nodes .node').count();
  const report = { url, checked_at: new Date().toISOString(), mode: 'Built Vite assets served by FastAPI; read-only production smoke', source_count: bootstrap.sources.length, workflow_nodes: nodes, research_status: bootstrap.meta.research_status, provider: bootstrap.meta.provider, page_errors: errors, failed_assets: failedAssets };
  if (errors.length || failedAssets.length || nodes !== 7) throw Error(JSON.stringify(report));
  await mkdir('../reports', { recursive: true });
  await writeFile('../reports/production-smoke.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
