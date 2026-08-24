#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { enhancePagesHtml } from './pages-money-ui.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, '.pages');
const API_OUT = path.join(OUT, 'api');

async function invoke(modulePath) {
  const mod = await import(path.join(ROOT, modulePath));
  const handler = mod.default;
  if (typeof handler !== 'function') throw new Error(`${modulePath} has no default handler`);
  let statusCode = 200;
  let body;
  const res = {
    setHeader() {},
    status(code) { statusCode = code; return this; },
    json(value) { body = value; return this; },
    send(value) { body = value; return this; },
    end(value) { if (value !== undefined) body = value; return this; }
  };
  await handler({ method: 'GET', query: {}, headers: {} }, res);
  if (statusCode < 200 || statusCode >= 300) {
    throw new Error(`${modulePath} returned HTTP ${statusCode}: ${JSON.stringify(body)}`);
  }
  if (body?.error) throw new Error(`${modulePath}: ${body.error}`);
  return body;
}

function assertClose(a, b, label) {
  if (a == null || b == null || Math.abs(a - b) > 0.0002) {
    throw new Error(`Pages ${label} history/Core mismatch: ${a} vs ${b}`);
  }
}

function assertRoundedScore(a, b, label) {
  if (a == null || b == null || Number(a.toFixed(1)) !== Number(b.toFixed(1))) {
    throw new Error(`Pages ${label} history/report mismatch after 1dp report rounding: ${a} vs ${b}`);
  }
}

async function main() {
  await fs.rm(OUT, { recursive: true, force: true });
  await fs.mkdir(API_OUT, { recursive: true });

  const [report, radar, history] = await Promise.all([
    invoke('api/report.js'),
    invoke('api/radar.js'),
    invoke('api/history.js')
  ]);

  const core = report?.regime?.engine_fact?.money;
  if (core?.version !== 'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL') {
    throw new Error('Pages snapshot is not using promoted Money V2');
  }
  if (report?.money_promotion_gate?.status !== 'PASS_MONEY_V2_PRODUCTION_PROMOTION') {
    throw new Error('Money V2 promotion gate is not PASS');
  }
  if (core?.available_date !== '2026-07-31') {
    throw new Error(`Unexpected active Money date ${core?.available_date}`);
  }

  const latest = history?.rows?.at(-1);
  if (!latest || latest.available_date !== core.available_date) {
    throw new Error(`Pages history/Core date mismatch: ${latest?.available_date} vs ${core.available_date}`);
  }
  assertClose(latest.usd_yoy_pct, core.usd_yoy_pct, 'USD YoY');
  assertClose(latest.fx_neutral_yoy_pct, core.fx_neutral_yoy_pct, 'FX-neutral YoY');
  assertRoundedScore(latest.usd_score, core.usd_score, 'USD score');
  assertRoundedScore(latest.fx_neutral_score, core.fx_neutral_score, 'FX-neutral score');

  await fs.writeFile(path.join(API_OUT, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  await fs.writeFile(path.join(API_OUT, 'radar.json'), JSON.stringify(radar, null, 2) + '\n');
  await fs.writeFile(path.join(API_OUT, 'history.json'), JSON.stringify(history, null, 2) + '\n');

  let html = await fs.readFile(path.join(ROOT, 'index.html'), 'utf8');
  html = enhancePagesHtml(html)
    .replaceAll("fetch('/api/report')", "fetch('./api/report.json', {cache:'no-store'})")
    .replaceAll("fetch('/api/radar')", "fetch('./api/radar.json', {cache:'no-store'})")
    .replaceAll("fetch('/api/history')", "fetch('./api/history.json', {cache:'no-store'})")
    .replaceAll('href="/api/report"', 'href="./api/report.json"')
    .replaceAll('href="/api/radar"', 'href="./api/radar.json"')
    .replaceAll('href="/api/history"', 'href="./api/history.json"')
    .replace('<div class="tag">GMLI 2.5 · Pareto liquidity decision cockpit</div>', '<div class="tag">GMLI 2.5 · GitHub Pages resilient cockpit</div>')
    .replace('Loading /api/report + /api/radar…', 'Loading verified static engine snapshot…');

  const apiBase = 'https://gmli-fred-dashboard.vercel.app';
  for (const endpoint of ['current-market','status','decision','opportunity','positioning','money-nowcast']) {
    html = html.replaceAll(`href="/api/${endpoint}"`, `href="${apiBase}/api/${endpoint}"`);
  }
  html = html.replace('</main>', '<div class="footer"><b>GitHub Pages:</b> Core, Money history and Radar snapshots are built directly from the repository engine/history. Raw live endpoints may still point to Vercel.</div></main>');
  await fs.writeFile(path.join(OUT, 'index.html'), html);
  await fs.writeFile(path.join(OUT, '.nojekyll'), '');

  console.log(JSON.stringify({
    status: 'PASS_GITHUB_PAGES_SNAPSHOT',
    money_version: core.version,
    money_available_date: core.available_date,
    usd_yoy_pct: core.usd_yoy_pct,
    fx_neutral_yoy_pct: core.fx_neutral_yoy_pct,
    history_start_month: history.start_month,
    history_latest_month: history.latest_month,
    history_rows: history.rows.length,
    report_schema: report.schema_version,
    radar_as_of: radar.as_of
  }, null, 2));
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
