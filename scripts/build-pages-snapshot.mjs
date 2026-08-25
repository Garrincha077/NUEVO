#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { enhancePagesHtml } from './pages-money-ui.mjs';
import { enhanceMobileInfo } from './pages-mobile-info.mjs';
import { enhanceSignalRoleUi } from './pages-signal-role-ui.mjs';
import { buildContextHistory } from './pages-context-history.mjs';

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

function writeJson(name, value) {
  return fs.writeFile(path.join(API_OUT, name), JSON.stringify(value, null, 2) + '\n');
}

async function main() {
  await fs.rm(OUT, { recursive: true, force: true });
  await fs.mkdir(API_OUT, { recursive: true });

  const [report, radar, history, status, moneyNowcast] = await Promise.all([
    invoke('api/report.js'),
    invoke('api/radar.js'),
    invoke('api/history.js'),
    invoke('api/status.js'),
    invoke('api/money-nowcast.js')
  ]);

  const core = report?.regime?.engine_fact?.money;
  const funding = report?.regime?.current_research_inference?.funding;
  const fiscal = report?.regime?.current_research_inference?.fiscal;
  const structuralMarket = report?.regime?.current_research_inference?.structural_market_confirmation;
  const roles = report?.signal_role_taxonomy;
  if (core?.version !== 'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL') {
    throw new Error('Pages snapshot is not using promoted Money V2');
  }
  if (report?.money_promotion_gate?.status !== 'PASS_MONEY_V2_PRODUCTION_PROMOTION') {
    throw new Error('Money V2 promotion gate is not PASS');
  }
  if (core?.available_date !== '2026-07-31') {
    throw new Error(`Unexpected active Money date ${core?.available_date}`);
  }
  if (fiscal?.version !== 'GMLI_FISCAL_V2_DEFICIT_IMPULSE') {
    throw new Error('Pages snapshot is not using promoted Fiscal V2');
  }
  if (report?.fiscal_promotion_gate?.status !== 'PASS_FISCAL_V2_PRODUCTION_PROMOTION') {
    throw new Error('Fiscal V2 promotion gate is not PASS');
  }
  if (report?.regime?.conviction?.max !== 10 || report?.regime?.conviction?.fiscal_v2_automatic_weight !== 0) {
    throw new Error('Frozen 10-point rubric or Fiscal zero-weight guard changed');
  }
  if (roles?.version !== 'GMLI_SIGNAL_ROLE_TAXONOMY_V1' || roles?.scoring_effect !== 'NONE' || roles?.automatic_weight_change !== 0) {
    throw new Error('Signal Role Taxonomy v1 guard failed');
  }
  if (roles?.money_core?.role !== 'LEADING' || roles?.funding_v2?.role !== 'REACTIVE_CONFIRMATION' || roles?.fiscal_v2?.role !== 'MIXED' || roles?.market_confirmation?.role !== 'REACTIVE_CONFIRMATION') {
    throw new Error('Signal Role Taxonomy role mapping changed');
  }

  const latest = history?.rows?.at(-1);
  if (!latest || latest.available_date !== core.available_date) {
    throw new Error(`Pages history/Core date mismatch: ${latest?.available_date} vs ${core.available_date}`);
  }
  assertClose(latest.usd_yoy_pct, core.usd_yoy_pct, 'USD YoY');
  assertClose(latest.fx_neutral_yoy_pct, core.fx_neutral_yoy_pct, 'FX-neutral YoY');
  assertRoundedScore(latest.usd_score, core.usd_score, 'USD score');
  assertRoundedScore(latest.fx_neutral_score, core.fx_neutral_score, 'FX-neutral score');

  const contextHistory = await buildContextHistory(ROOT, report);
  const latestFundingHistory = contextHistory?.funding?.rows?.at(-1);
  const latestFiscalHistory = contextHistory?.fiscal?.rows?.at(-1);
  const latestMarketHistory = contextHistory?.market_confirmation?.rows?.at(-1);
  if (!latestFundingHistory || !latestFiscalHistory || !latestMarketHistory) {
    throw new Error('Context history is incomplete');
  }
  assertRoundedScore(latestFundingHistory.score, funding?.score, 'Funding V2');
  assertRoundedScore(latestFiscalHistory.score, fiscal?.score, 'Fiscal V2');
  if (latestFundingHistory.available_date !== funding?.available_date) {
    throw new Error(`Funding context history date mismatch: ${latestFundingHistory.available_date} vs ${funding?.available_date}`);
  }
  if (latestFiscalHistory.available_date !== fiscal?.available_date) {
    throw new Error(`Fiscal context history date mismatch: ${latestFiscalHistory.available_date} vs ${fiscal?.available_date}`);
  }
  if (latestMarketHistory.positive !== structuralMarket?.positive || latestMarketHistory.score_0_2 !== structuralMarket?.score_0_2) {
    throw new Error(`Market context history latest mismatch: ${latestMarketHistory.positive}/${latestMarketHistory.score_0_2} vs ${structuralMarket?.positive}/${structuralMarket?.score_0_2}`);
  }

  const decisionSnapshot = {
    schema_version: 'gmli-pages-decision-snapshot-v1',
    source: 'DERIVED_FROM_CANONICAL_REPORT_SNAPSHOT',
    generated_at: report.generated_at,
    methodology: report.methodology,
    signal_role_taxonomy: roles,
    money: report.regime.engine_fact.money,
    money_nowcast: report.regime.current_research_inference.money_nowcast,
    funding: report.regime.current_research_inference.funding,
    fiscal: report.regime.current_research_inference.fiscal,
    market_confirmation: report.regime.current_research_inference.structural_market_confirmation,
    current_market_confirmation: report.current_market_confirmation,
    conviction: report.regime.conviction,
    freshness: report.regime.freshness,
    money_promotion_gate: report.money_promotion_gate,
    funding_promotion_gate: report.funding_promotion_gate,
    fiscal_promotion_gate: report.fiscal_promotion_gate
  };
  const opportunitySnapshot = {
    schema_version: 'gmli-pages-opportunity-snapshot-v1',
    source: 'DERIVED_FROM_CANONICAL_REPORT_SNAPSHOT',
    generated_at: report.generated_at,
    summary: report.opportunity_summary,
    assets: report.assets,
    conflicts: report.conflicts
  };
  const positioningSnapshot = {
    schema_version: 'gmli-pages-positioning-snapshot-v1',
    source: 'DERIVED_FROM_CANONICAL_REPORT_SNAPSHOT',
    generated_at: report.generated_at,
    assets: Object.fromEntries(Object.entries(report.assets || {}).map(([asset, row]) => [asset, row.positioning || null]))
  };

  await Promise.all([
    writeJson('report.json', report),
    writeJson('radar.json', radar),
    writeJson('history.json', history),
    writeJson('status.json', status),
    writeJson('money-nowcast.json', moneyNowcast),
    writeJson('current-market.json', report.current_market_confirmation),
    writeJson('decision.json', decisionSnapshot),
    writeJson('opportunity.json', opportunitySnapshot),
    writeJson('positioning.json', positioningSnapshot),
    writeJson('context-history.json', contextHistory)
  ]);

  let html = await fs.readFile(path.join(ROOT, 'index.html'), 'utf8');
  html = enhanceSignalRoleUi(enhanceMobileInfo(enhancePagesHtml(html)))
    .replaceAll("fetch('/api/report')", "fetch('./api/report.json', {cache:'no-store'})")
    .replaceAll("fetch('/api/radar')", "fetch('./api/radar.json', {cache:'no-store'})")
    .replaceAll("fetch('/api/history')", "fetch('./api/history.json', {cache:'no-store'})")
    .replaceAll('href="/api/report"', 'href="./api/report.json"')
    .replaceAll('href="/api/radar"', 'href="./api/radar.json"')
    .replaceAll('href="/api/history"', 'href="./api/history.json"')
    .replace('<div class="tag">GMLI 2.5 · Pareto liquidity decision cockpit</div>', '<div class="tag">GMLI 2.5 · GitHub Pages resilient cockpit</div>')
    .replace('Loading /api/report + /api/radar…', 'Loading verified static engine snapshot…');

  for (const endpoint of ['current-market','status','decision','opportunity','positioning','money-nowcast']) {
    html = html.replaceAll(`href="/api/${endpoint}"`, `href="./api/${endpoint}.json"`);
  }
  html = html.replace('</main>', '<div class="footer"><b>GitHub Pages:</b> verified static Money Core, Funding/Fiscal/Market history, signal-role taxonomy, market confirmation, decision context, nowcast, Money history and Radar snapshots are built directly from the repository. Vercel is not required for the core fallback view.</div></main>');
  await fs.writeFile(path.join(OUT, 'index.html'), html);
  await fs.writeFile(path.join(OUT, '.nojekyll'), '');

  console.log(JSON.stringify({
    status: 'PASS_GITHUB_PAGES_SNAPSHOT',
    money_version: core.version,
    money_available_date: core.available_date,
    fiscal_version: fiscal.version,
    fiscal_available_date: fiscal.available_date,
    fiscal_score: fiscal.score,
    fiscal_regime: fiscal.regime,
    fiscal_automatic_weight: report.regime.conviction.fiscal_v2_automatic_weight,
    signal_role_taxonomy: roles.version,
    signal_role_scoring_effect: roles.scoring_effect,
    usd_yoy_pct: core.usd_yoy_pct,
    fx_neutral_yoy_pct: core.fx_neutral_yoy_pct,
    history_start_month: history.start_month,
    history_latest_month: history.latest_month,
    history_rows: history.rows.length,
    context_funding_history_rows: contextHistory.funding.rows.length,
    context_fiscal_history_rows: contextHistory.fiscal.rows.length,
    context_market_history_rows: contextHistory.market_confirmation.rows.length,
    context_market_latest_month: latestMarketHistory.month,
    report_schema: report.schema_version,
    static_api_files: 10,
    pages_context_ui: true,
    pages_context_history_ui: true,
    radar_as_of: radar.as_of
  }, null, 2));
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
