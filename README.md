# detailingrv — сайт-портфоліо

Концепт сайту детейлінг-студії для портфоліо: https://detailingrv.pages.dev/
Хостинг — Cloudflare Pages (автодеплой з гілки main), заявки з форми — у Telegram.

- Дані сайту: `clients/detailingrv.json`; дизайн: `template.html`.
- Після правок: `python3 build.py clients/detailingrv.json --out index.html`, потім коміт і push.
- Форма: `functions/api/estimate.js` → `lib/estimate-core.mjs` → Telegram. Змінні в Cloudflare: `TELEGRAM_BOT_TOKEN` (Secret), `TELEGRAM_CHAT_ID`.
- Cloudflare: Build command `bash tools/cf-build.sh`, Build output directory `public`.
- Гілка `demo/zakhar` — демо з фото Захара (окрема прев'ю-адреса Cloudflare).

Сайти для реальних клієнтів робимо в окремих репозиторіях (наприклад, `detailing-client`), а не тут.
