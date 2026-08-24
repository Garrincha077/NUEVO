#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

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

async function main() {
  await fs.rm(OUT, { recursive: true, force: true });
  await fs.mkdir(API_OUT, { recursive: true });

  // Fail closed: Pages is published only if the two cockpit contracts build successfully
  // from the same main-branch engine code used by production.
  const [report, radar] = await Promise.all([
    invoke('api/report.js'),
    invoke('api/radar.js')
  ]);

  if (report?.regime?.engine_fact?.money?.version !== 'GMLI_GLOBAL_MONEY_V2_PBOC_OFFICIAL') {
    throw new Error('Pages snapshot is not using promoted Money V2');
  }
  if (report?.money_promotion_gate?.status !== 'PASS_MONEY_V2_PRODUCTION_PROMOTION') {
    throw new Error('Money V2 promotion gate is not PASS');
  }
  if (report?.regime?.engine_fact?.money?.available_date !== '2026-07-31') {
    throw new Error(`Unexpected active Money date ${report?.regime?.engine_fact?.money?.available_date}`);
  }

  await fs.writeFile(path.join(API_OUT, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  await fs.writeFile(path.join(API_OUT, 'radar.json'), JSON.stringify(radar, null, 2) + '\n');

  let html = await fs.readFile(path.join(ROOT, 'index.html'), 'utf8');
  html = html
    .replaceAll("fetch('/api/report')", "fetch('./api/report.json', {cache:'no-store'})")
    .replaceAll("fetch('/api/radar')", "fetch('./api/radar.json', {cache:'no-store'})")
    .replaceAll('href="/api/report"', 'href="./api/report.json"')
    .replaceAll('href="/api/radar"', 'href="./api/radar.json"')
    .replace('<div class="tag">GMLI 2.5 · Pareto liquidity decision cockpit</div>', '<div class="tag">GMLI 2.5 · GitHub Pages resilient cockpit</div>')
    .replace('Loading /api/report + /api/radar…', 'Loading verified static engine snapshot…')
    .replace('<div class="tag">ENGINE FACT · USD Money</div>', '<div class="tag">ENGINE FACT · Global Money · USD-translated</div>')
    .replace('<div class="tag">ENGINE FACT · FX-neutral</div>', '<div class="tag">ENGINE FACT · Global Money · FX-neutral</div>')
    .replace("usd.textContent=m.usd_score.toFixed(1);usdRegime.textContent=m.usd_regime+' · '+m.available_date;fxn.textContent=m.fx_neutral_score.toFixed(1);fxnRegime.textContent=m.fx_neutral_regime+' · '+m.agreement;", "usd.textContent=(m.usd_yoy_pct>=0?'+':'')+m.usd_yoy_pct.toFixed(2)+'% YoY';usdRegime.innerHTML='Score <b>'+m.usd_score.toFixed(1)+'</b> · '+m.usd_regime+' · '+m.available_date+'<br><span class=\"small muted\">FX contribution ≈ '+(m.usd_yoy_pct-m.fx_neutral_yoy_pct>=0?'+':'')+(m.usd_yoy_pct-m.fx_neutral_yoy_pct).toFixed(2)+' pp</span>';fxn.textContent=(m.fx_neutral_yoy_pct>=0?'+':'')+m.fx_neutral_yoy_pct.toFixed(2)+'% YoY';fxnRegime.innerHTML='Score <b>'+m.fx_neutral_score.toFixed(1)+'</b> · '+m.fx_neutral_regime+' · '+m.agreement+'<br><span class=\"small muted\">Underlying global broad-money growth, FX-neutral</span>';" )
    .replace("fresh.innerHTML=`<b>ENGINE FACT:</b> Core ${m.available_date} (${m.freshness}). <b>NOWCAST:</b>", "fresh.innerHTML=`<b>GLOBAL MONEY:</b> USD-translated ${(m.usd_yoy_pct>=0?'+':'')+m.usd_yoy_pct.toFixed(2)}% YoY · FX-neutral ${(m.fx_neutral_yoy_pct>=0?'+':'')+m.fx_neutral_yoy_pct.toFixed(2)}% YoY. <b>ENGINE FACT:</b> Core ${m.available_date} (${m.freshness}). <b>NOWCAST:</b>");

  const apiBase = 'https://gmli-fred-dashboard.vercel.app';
  for (const endpoint of ['current-market','status','decision','opportunity','positioning','money-nowcast']) {
    html = html.replaceAll(`href="/api/${endpoint}"`, `href="${apiBase}/api/${endpoint}"`);
  }
  html = html.replace('</main>', '<div class="footer"><b>GitHub Pages fallback:</b> Core/decision snapshot is built directly from the repository engine. Raw live endpoints may still point to Vercel.</div></main>');
  await fs.writeFile(path.join(OUT, 'index.html'), html);
  await fs.writeFile(path.join(OUT, '.nojekyll'), '');

  console.log(JSON.stringify({
    status: 'PASS_GITHUB_PAGES_SNAPSHOT',
    money_version: report.regime.engine_fact.money.version,
    money_available_date: report.regime.engine_fact.money.available_date,
    usd_yoy_pct: report.regime.engine_fact.money.usd_yoy_pct,
    fx_neutral_yoy_pct: report.regime.engine_fact.money.fx_neutral_yoy_pct,
    report_schema: report.schema_version,
    radar_as_of: radar.as_of
  }, null, 2));
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
