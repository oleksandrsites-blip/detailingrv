// Cloudflare Pages Function: адреса /api/estimate (за шляхом файлу).
// Змінні TELEGRAM_BOT_TOKEN і TELEGRAM_CHAT_ID задаються в Cloudflare → проєкт → Settings → Variables and Secrets.
import { handle } from '../../lib/estimate-core.mjs';

export const onRequestPost = ({ request, env }) => handle(request, env);
