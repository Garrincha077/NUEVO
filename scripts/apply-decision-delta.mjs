#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildDecisionDelta, enhanceDecisionDeltaUi } from './pages-decision-delta.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, '.pages');
const API = path.join(OUT, 'api');

async function readJson(name) {
  return JSON.parse(await fs.readFile(path.join(API, name), 'utf8'));
}

async function writeJson(name, value) {
  await fs.writeFile(path.join(API, name), JSON.stringify(value, null, 2) + '\n');
}

function assert(value, message) {
  if (!value) throw new Error(message);
}

function enhanceVerifiedPagesHtml(rawHtml) {
  const contextLink = '<a href="#contextLayers">CONTEXT</a>';
  const hadContextLink = rawHtml.includes(contextLink);
  let prepared = hadContextLink ? rawHtml.replace(contextLink, '') : rawHtml;
  let enhanced = enhanceDecisionDeltaUi(prepared);
  if (hadContextLink) {
    const marker = '<a href="#decisionBrief">DECISION</a><a href="#moneyTrend">MONEY TREND</a>';
    const replacement = '<a href="#decisionBrief">DECISION</a><a href="#contextLayers">CONTEXT</a><a href="#moneyTrend">MONEY TREND</a>';
    assert(enhanced.includes(marker), 'Decision Delta UI context-nav restore marker missing');
    enhanced = enhanced.replace(marker, replacement);
  }
  return enhanced;
}

async function main() {
  const [report, history, contextHistory, decision] = await Promise.all([
    readJson('report.json'),
    readJson('history.json'),
    readJson('context-history.json'),
    readJson('decision.json')
  ]);

  assert(report?.regime?.conviction?.max === 10, 'Decision Delta guard: conviction max changed');
  assert(report?.regime?.conviction?.fiscal_v2_automatic_weight === 0, 'Decision Delta guard: Fiscal automatic weight changed');
  assert(report?.signal_role_taxonomy?.scoring_effect === 'NONE', 'Decision Delta guard: role taxonomy scoring effect changed');

  const layer = buildDecisionDelta(report, history, contextHistory);
  assert(layer?.decision_delta?.scoring_effect === 'NONE', 'Decision Delta scoring effect must remain NONE');
  assert(layer?.decision_delta?.automatic_weight_change === 0, 'Decision Delta automatic weight change must remain 0');
  assert(layer?.decision_delta?.conviction?.fiscal_v2_automatic_weight === 0, 'Decision Delta Fiscal weight guard failed');
  assert(layer?.decision_brief?.scoring_effect === 'NONE', 'Decision Brief scoring effect must remain NONE');

  report.decision_delta = layer.decision_delta;
  report.decision_brief = layer.decision_brief;
  report.meta = {
    ...(report.meta || {}),
    decision_delta: {
      status: 'AVAILABLE_ON_GITHUB_PAGES',
      schema_version: layer.decision_delta.schema_version,
      scoring_effect: 'NONE',
      endpoint: './api/decision-delta.json'
    }
  };

  decision.decision_delta = layer.decision_delta;
  decision.decision_brief = layer.decision_brief;

  await Promise.all([
    writeJson('report.json', report),
    writeJson('decision.json', decision),
    writeJson('decision-delta.json', {
      ...layer,
      source: 'DERIVED_FROM_VERIFIED_GITHUB_PAGES_SNAPSHOT',
      guardrail: 'Presentation/research diagnostic only. Frozen Money/Funding/Fiscal methodology and the 10-point conviction rubric are unchanged.'
    })
  ]);

  const htmlPath = path.join(OUT, 'index.html');
  const html = enhanceVerifiedPagesHtml(await fs.readFile(htmlPath, 'utf8'));
  await fs.writeFile(htmlPath, html);

  console.log(JSON.stringify({
    status: 'PASS_GMLI_DECISION_DELTA',
    decision_delta_schema: layer.decision_delta.schema_version,
    decision_brief_schema: layer.decision_brief.schema_version,
    scoring_effect: layer.decision_delta.scoring_effect,
    automatic_weight_change: layer.decision_delta.automatic_weight_change,
    current_conviction: layer.decision_delta.conviction.current,
    previous_conviction_proxy: layer.decision_delta.conviction.previous_proxy,
    money_usd_delta: layer.decision_delta.money.usd.delta,
    money_fxn_delta: layer.decision_delta.money.fx_neutral.delta,
    funding_delta: layer.decision_delta.funding.delta,
    fiscal_delta: layer.decision_delta.fiscal.delta,
    market_delta: layer.decision_delta.market_confirmation.delta_score_0_2,
    pages_decision_brief_ui: true
  }, null, 2));
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
