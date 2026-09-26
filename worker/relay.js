// Cloudflare Worker: (1) Telegram mesajını GitHub Actions "Sohbet" workflow'una iletir,
// (2) cron ile her akşam "Akşam özeti" workflow'unu tetikler.
//
// Ayarlar (Worker -> Settings -> Variables and Secrets):
//   WEBHOOK_SECRET    (secret)  Telegram'a verilen secret_token ile aynı değer
//   GITHUB_TOKEN      (secret)  Sadece bu repoya, "Contents: Read and write" yetkili fine-grained token
//   ALLOWED_CHAT_ID   (text)    Sadece bu sohbetten gelen mesajlar işlenir
//   GITHUB_REPO       (text)    beatek06/takvimagent
//
// Cron (Worker -> Settings -> Triggers -> Cron Triggers, saatler UTC):
//   0 17 * * *   ve   0 18 * * *
// Zürih 19:00 yazın 17:00 UTC, kışın 18:00 UTC'dir. İkisi de tetiklenir; Python kodu
// saati ve "bugün gönderildi mi" bilgisini kontrol edip fazlasını atlar.

async function dispatch(env, eventType, payload) {
  const res = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "takvim-relay",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ event_type: eventType, client_payload: payload }),
  });
  if (!res.ok) console.log("GitHub dispatch hatası", eventType, res.status, await res.text());
  return res.ok;
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("ok");

    // Telegram'ın webhook'u kurarken belirlediğimiz gizli başlığı gönderdiğini doğrula.
    if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }

    const update = await request.json();
    const msg = update.message;
    // Sadece senin sohbetinden gelen metin mesajları; diğerlerini sessizce yok say.
    if (!msg || !msg.text || String(msg.chat.id) !== String(env.ALLOWED_CHAT_ID)) {
      return new Response("ok");
    }

    await dispatch(env, "telegram-message", {
      text: msg.text,
      chat_id: String(msg.chat.id),
      reply_to: (msg.reply_to_message && msg.reply_to_message.text) || "",
    });

    // Her zaman 200: aksi hâlde Telegram aynı mesajı tekrar tekrar gönderir.
    return new Response("ok");
  },

  // Cron Triggers burayı çağırır.
  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatch(env, "evening-summary", {}));
  },
};
