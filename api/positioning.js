import { buildPositioning } from '../lib/cftc-positioning.js';
export default async function handler(req,res){res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('Cache-Control','public, max-age=0, must-revalidate');try{return res.status(200).json(await buildPositioning());}catch(e){return res.status(500).json({error:e.message,endpoint:'/api/positioning'});}}
