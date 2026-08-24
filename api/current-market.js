import { buildOpportunity } from '../lib/opportunity-engine.js';
import { buildCurrentMarketConfirmation } from '../lib/current-market.js';

export default async function handler(req,res){
  res.setHeader('Access-Control-Allow-Origin','*');
  res.setHeader('Cache-Control','public, max-age=300, stale-while-revalidate=900');
  try {
    const opportunity = await buildOpportunity();
    return res.status(200).json(await buildCurrentMarketConfirmation(opportunity));
  } catch(e) {
    return res.status(500).json({error:e.message,endpoint:'/api/current-market'});
  }
}
