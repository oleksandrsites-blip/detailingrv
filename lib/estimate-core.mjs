// Заявка «Оцінити авто за фото» → Telegram-бот. Спільний код для Cloudflare Pages і Netlify.
// Токен і chat_id беруться ТІЛЬКИ зі змінних середовища хостингу:
//   TELEGRAM_BOT_TOKEN — токен від @BotFather
//   TELEGRAM_CHAT_ID   — куди слати (ваш особистий id або id групи)
// Сторонніх бібліотек немає: Node 18+ уміє FormData, Blob і fetch.

const MAX_PHOTOS = 5;
const MAX_PHOTO_BYTES = 5 * 1024 * 1024; // Telegram приймає фото до 10 МБ, у нас після стиснення ~0,3–1 МБ

const json = (status, body) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });

// HTML-режим Telegram: екрануємо все, що прийшло від користувача
const esc = (v) => String(v ?? '').trim().slice(0, 1000)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export async function handle(req, env) {
  if (req.method !== 'POST') return json(405, { ok: false, error: 'method' });

  const token = env.TELEGRAM_BOT_TOKEN;
  const chatId = env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) return json(500, { ok: false, error: 'not-configured' });

  let form;
  try { form = await req.formData(); } catch { return json(400, { ok: false, error: 'bad-form' }); }

  // пастка для ботів: справжні люди це поле не бачать
  if (form.get('bot-field')) return json(200, { ok: true });

  const name = esc(form.get('name'));
  const phone = esc(form.get('phone'));
  const car = esc(form.get('car'));
  const message = esc(form.get('message'));
  const site = esc(form.get('site')) || 'сайт';
  if (!name || !phone || !car) return json(400, { ok: false, error: 'required' });

  const photos = [];
  for (let i = 1; i <= MAX_PHOTOS; i++) {
    const f = form.get('photo' + i);
    if (f && typeof f === 'object' && f.size > 0 && f.size <= MAX_PHOTO_BYTES && /^image\//.test(f.type || 'image/jpeg')) photos.push(f);
  }

  const tel = phone.replace(/[^\d+]/g, '');
  const text = [
    `<b>Нова заявка: оцінка авто за фото</b>`,
    `<i>${site}</i>`,
    ``,
    `👤 ${name}`,
    `📞 <a href="tel:${tel}">${phone}</a>`,
    `🚗 ${car}`,
    message ? `💬 ${message}` : null,
    `📷 Фото: ${photos.length}`,
  ].filter((l) => l !== null).join('\n');

  const api = (method, body) => fetch(`https://api.telegram.org/bot${token}/${method}`, { method: 'POST', body })
    .then(async (r) => { const d = await r.json().catch(() => ({})); if (!r.ok || !d.ok) throw new Error(`${method}: ${d.description || r.status}`); return d; });

  try {
    // 1) текст заявки
    const tf = new FormData();
    tf.set('chat_id', chatId); tf.set('text', text); tf.set('parse_mode', 'HTML'); tf.set('disable_web_page_preview', 'true');
    await api('sendMessage', tf);

    // 2) фото одним альбомом (або одне фото)
    if (photos.length === 1) {
      const pf = new FormData();
      pf.set('chat_id', chatId);
      pf.set('photo', photos[0], 'photo1.jpg');
      pf.set('caption', `${name}, ${car}`);
      await api('sendPhoto', pf);
    } else if (photos.length > 1) {
      const mf = new FormData();
      mf.set('chat_id', chatId);
      mf.set('media', JSON.stringify(photos.map((_, i) => ({
        type: 'photo', media: `attach://p${i}`, ...(i === 0 ? { caption: `${name}, ${car}` } : {}),
      }))));
      photos.forEach((p, i) => mf.set(`p${i}`, p, `photo${i + 1}.jpg`));
      await api('sendMediaGroup', mf);
    }
    return json(200, { ok: true, photos: photos.length });
  } catch (e) {
    console.error('telegram', e.message);
    return json(502, { ok: false, error: 'telegram' });
  }
}
