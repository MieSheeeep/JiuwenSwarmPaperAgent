import { test, expect } from '@playwright/test';

test('real artifacts, navigation, filtering, evidence dialog and resources', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /^让 Agent 在有限记忆中/ })).toBeVisible();
  await expect(page.locator('.stat-value').filter({ hasText: '240,721' })).toBeVisible();
  await expect(page.locator('.stat-value').filter({ hasText: '83.3%' })).toBeVisible();
  await page.getByRole('button', { name: '512 tokens', exact: true }).click();
  await expect(page.locator('.bar-row')).toHaveCount(7);
  await page.getByRole('button', { name: '256 tokens', exact: true }).click();
  await expect(page.locator('.bar-row')).toHaveCount(8);
  await page.screenshot({ path: '../output/workbench-preview/overview.png', fullPage: true, animations: 'disabled' });
  await page.getByRole('link', { name: '实验中心', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(10);
  await expect(page.locator('.filter-summary')).toContainText('192');
  await page.getByLabel('策略', { exact: true }).selectOption('versioned');
  await expect(page.locator('.filter-summary')).toContainText('20/24');
  await page.getByRole('button', { name: /^查看 .* 详情$/ }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('Ground truth');
  await expect(page.locator('.context-pre')).toContainText('valid_at');
  await page.getByRole('button', { name: '关闭详情' }).click();
  await page.getByLabel('结果', { exact: true }).selectOption('wrong');
  await expect(page.locator('.filter-summary')).toContainText('匹配 4 个条件');
  await page.getByLabel('搜索任务').fill('no-such-task-xxxxx');
  await expect(page.getByRole('heading', { name: '没有匹配的实验' })).toBeVisible();
  await page.getByRole('button', { name: '重置筛选', exact: true }).first().click();
  await page.screenshot({ path: '../output/workbench-preview/experiments.png', fullPage: true, animations: 'disabled' });
  await page.getByRole('link', { name: '论文与评审', exact: true }).click();
  await expect(page.getByText('评审与 PDF 版本匹配', { exact: true })).toBeVisible();
  await expect(page.getByTitle('English research manuscript PDF')).toBeVisible();
  await page.getByRole('tab', { name: '英文评审原文' }).click();
  await expect(page.locator('.review-original')).toContainText('4.5/10');
  await page.getByRole('link', { name: '资源与交付', exact: true }).click();
  await expect(page.locator('.download-grid .file-link')).toHaveCount(10);
  const downloadPending = page.waitForEvent('download');
  await page.locator('.download-grid .file-link').filter({ hasText: 'Resource report' }).click();
  const download = await downloadPending;
  expect(download.suggestedFilename()).toBe('resources.json');
  await expect(page.locator('.budget-label')).toContainText('80.2%');
  expect(errors).toEqual([]);
});

test('mobile layout, navigation and keyboard dialog dismissal', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.locator('.stat-value').filter({ hasText: '240,721' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.locator('.sidebar')).not.toBeVisible();
  await page.screenshot({ path: '../output/workbench-preview/mobile.png', fullPage: true, animations: 'disabled' });
  await page.getByRole('button', { name: '切换导航' }).click();
  await expect(page.getByRole('button', { name: '切换导航' })).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('link', { name: '实验中心', exact: true }).click();
  await page.getByRole('button', { name: /^查看 .* 详情$/ }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('API failure offers retry; missing runs show empty state', async ({ page }) => {
  await page.route('**/api/runs', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('暂时无法读取项目数据');
  await page.unroute('**/api/runs');
  await page.route('**/api/runs', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.getByRole('button', { name: '重新连接' }).click();
  await expect(page.getByRole('heading', { name: '还没有可查看的研究版本' })).toBeVisible();
});

test('missing results are shown as artifact failure, not a filter miss', async ({ page }) => {
  await page.route('**/cases', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }));
  await page.goto('/#experiments');
  await expect(page.getByRole('heading', { name: '实验记录暂不可用' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '没有匹配的实验' })).not.toBeVisible();
  await page.unroute('**/cases');
  await page.getByRole('button', { name: '重试', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(10);
});

test('error analysis, revision save, figure skill and LaTeX compilation', async ({ page }) => {
  test.setTimeout(100000);
  await page.goto('/#analysis');
  await expect(page.getByRole('heading', {name:'主条件错误分解'})).toBeVisible();
  await expect(page.locator('.stat-value').filter({hasText:'147'})).toBeVisible();
  await expect(page.locator('.failure-list details')).toHaveCount(5);
  await page.getByRole('link',{name:'写作与绘图',exact:true}).click();
  await expect(page.getByLabel('English section editor')).toBeVisible();
  await expect(page.getByLabel('English section editor')).toBeEditable();
  const previous = await page.getByLabel('English section editor').inputValue();
  await page.getByLabel('English section editor').fill(previous + ' This editable revision requires independent external review.');
  await expect(page.getByRole('button',{name:'刷新数据'})).toBeDisabled();
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('link',{name:'资源与交付',exact:true}).click();
  await expect(page.getByLabel('English section editor')).toHaveValue(previous + ' This editable revision requires independent external review.');
  await page.getByRole('button',{name:/保存新版本|保存为新修订/}).click();
  await expect(page.getByRole('status')).toContainText('已保存新修订');
  await page.getByRole('button',{name:'生成的 LaTeX'}).click();
  await expect(page.locator('.source-view')).toContainText('UNREVIEWED WORKBENCH REVISION');
  await page.getByRole('button',{name:'版本差异'}).click();
  await expect(page.locator('.source-view')).toContainText('This editable revision requires independent external review.');
  await expect(page.locator('.skill-card')).toHaveCount(3);
  let pollingFailures=0;
  await page.route(/\/jobs\/j_[a-f0-9]+$/, route => {
    if(route.request().method()==='GET' && pollingFailures===0) { pollingFailures++; return route.fulfill({status:503,contentType:'application/json',body:'{}'}); }
    return route.continue();
  });
  await page.getByRole('button',{name:'编译新修订 PDF'}).click();
  await expect(page.locator('.job-heading .badge')).toHaveText('succeeded',{timeout:85000});
  expect(pollingFailures).toBe(1);
  await expect(page.getByTitle('Unreviewed revision PDF')).toBeVisible();
  await expect(page.locator('.figure-previews img')).toHaveCount(2);
  await expect(page.locator('.job-downloads')).toContainText('figure_manifest.json');
  await page.screenshot({path:'../output/workbench-preview/writing-studio.png',fullPage:true,animations:'disabled'});
  const response = await page.request.get('/api/runs/memory_live_20261016/files/paper');
  expect(response.ok()).toBeTruthy();
});

test('new study is independent of legacy runs and exposes only report downloads',async({page})=>{
  await page.route('**/api/runs',route=>route.fulfill({status:200,contentType:'application/json',body:'[]'}));
  await page.goto('/#upgrade');
  await expect(page.getByRole('heading',{name:'逐项补证据，完整记录结果。'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'评审缺口与实施状态'})).toBeVisible();
  await expect(page.locator('.gap-card')).toHaveCount(10);
  await expect(page.getByText('独立新研究 · 20261106',{exact:true})).toBeVisible();
  await expect(page.locator('.stat-note').filter({hasText:'3,000,000'})).toBeVisible();
  await page.getByLabel('升级测试集合').selectOption('synthetic_controlled');
  await expect(page.getByLabel('升级测试集合')).toHaveValue('synthetic_controlled');
  await expect(page.getByLabel('升级测试集合').locator('option:checked')).toHaveText('合成主测试 72 题');
  await expect(page.locator('a[href*="calls.jsonl"]')).toHaveCount(0);
  await page.screenshot({path:'../output/workbench-preview/research-upgrade.png',fullPage:true,animations:'disabled'});
});
