import fs from 'node:fs/promises';
import path from 'node:path';
import { CONTEXT_ASSETS, buildContextHistoryFromInputs } from './context-history-core.mjs';

export async function buildContextHistory(root, report) {
  const [fundingCsv, fiscalCsv, pricePairs] = await Promise.all([
    fs.readFile(path.join(root, 'research/funding-v2/latest/history.csv'), 'utf8'),
    fs.readFile(path.join(root, 'research/fiscal-v2/latest/history.csv'), 'utf8'),
    Promise.all(CONTEXT_ASSETS.map(async asset => [
      asset,
      JSON.parse(await fs.readFile(path.join(root, `research/global-money-v2/transfer/latest/raw/${asset}-yahoo-monthly.json`), 'utf8'))
    ]))
  ]);

  return buildContextHistoryFromInputs(report, {
    funding_csv: fundingCsv,
    fiscal_csv: fiscalCsv,
    price_json: Object.fromEntries(pricePairs)
  });
}
