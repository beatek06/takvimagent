// Cloudflare Worker: Telegram mesajını GitHub Actions "Sohbet" workflow'una iletir.
//
// Ayarlar (Worker -> Settings -> Variables and Secrets):
//   WEBHOOK_SECRET    (secret)  Telegram'a verilen secret_token ile aynı değer
//   GITHUB_TOKEN      (secret)  Sadece bu repoya, "Contents: Read and write" yetkili fine-grained token
//   ALLOWED_CHAT_ID   (text)    Sadece bu sohbetten gelen mesajlar işlenir
//   GITHUB_REPO       (text)    beatek06/takvimagent

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

    const res = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "takvim-relay",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        event_type: "telegram-message",
        client_payload: {
          text: msg.text,
          chat_id: String(msg.chat.id),
          reply_to: (msg.reply_to_message && msg.reply_to_message.text) || "",
        },
      }),
    });
    if (!res.ok) console.log("GitHub dispatch hatası", res.status, await res.text());

    // Her zaman 200: aksi hâlde Telegram aynı mesajı tekrar tekrar gönderir.
    return new Response("ok");
  },
};
