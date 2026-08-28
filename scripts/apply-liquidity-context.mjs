#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildLiquidityContext, enhanceLiquidityContext } from './pages-liquidity-context.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PAGES = path.join(ROOT, '.pages');
const API = path.join(PAGES, 'api');

async function main() {
  const context = await buildLiquidityContext();
  if (context.version !== 'GMLI_LIQUIDITY_CONTEXT_V1') throw new Error('Unexpected liquidity context version');
  if (context.evidence_tier !== 'RESEARCH_DIAGNOSTIC') throw new Error('Liquidity context evidence tier changed');
  if (context.scoring_effect !== 'NONE' || context.automatic_weight_change !== 0 || context.methodology_effect !== 'NONE') {
    throw new Error('Liquidity context zero-scoring guard failed');
  }

  await fs.mkdir(API, { recursive: true });
  await fs.writeFile(path.join(API, 'liquidity-context.json'), JSON.stringify(context, null, 2) + '\n');

  const htmlPath = path.join(PAGES, 'index.html');
  const html = await fs.readFile(htmlPath, 'utf8');
  const enhanced = enhanceLiquidityContext(html, context);
  if (!enhanced.includes('id="liquidityContext"') || !enhanced.includes('liquidity-context.json')) {
    throw new Error('Liquidity context UI integration failed');
  }
  if (enhanced.includes('id="bankImpulseDirection">Loading') || enhanced.includes('Loading liquidity context')) {
    throw new Error('Liquidity context must be statically rendered in the published snapshot');
  }
  await fs.writeFile(htmlPath, enhanced);

  console.log(JSON.stringify({
    status: 'PASS_GMLI_LIQUIDITY_CONTEXT',
    schema_version: context.schema_version,
    version: context.version,
    evidence_tier: context.evidence_tier,
    scoring_effect: context.scoring_effect,
    automatic_weight_change: context.automatic_weight_change,
    methodology_effect: context.methodology_effect,
    bank_status: context.bank_balance_sheet_impulse.status,
    bank_latest_date: context.bank_balance_sheet_impulse.latest_date || null,
    treasury_status: context.treasury_duration_mix.status,
    treasury_latest_date: context.treasury_duration_mix.latest_date || null,
    pages_liquidity_context_ui: true,
    pages_liquidity_context_static_render: true
  }, null, 2));
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
