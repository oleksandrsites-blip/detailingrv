// Netlify: адреса /api/estimate. Уся логіка — у lib/estimate-core.mjs.
import { handle } from '../../lib/estimate-core.mjs';

export default (req) => handle(req, process.env);

export const config = { path: '/api/estimate' };
