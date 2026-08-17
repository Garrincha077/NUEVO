import { FROZEN_STATE } from '../lib/state.js';
export default function handler(req,res){res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('Cache-Control','public, max-age=0, must-revalidate');return res.status(200).json(FROZEN_STATE);}
