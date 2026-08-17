import { getLiveMoneyNowcast } from '../lib/live-money-nowcast.js';
export default async function handler(req,res){
  res.setHeader('Access-Control-Allow-Origin','*');
  res.setHeader('Cache-Control','public, s-maxage=1800, stale-while-revalidate=3600');
  if(req.method!=='GET'){res.setHeader('Allow','GET');return res.status(405).json({error:'METHOD_NOT_ALLOWED'});}
  try{return res.status(200).json(await getLiveMoneyNowcast());}
  catch(e){return res.status(500).json({error:e.message,endpoint:'/api/money-nowcast'});}
}
