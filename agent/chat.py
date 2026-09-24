"""Telegram mesajını alıp modelle takvimi/dosyayı düzenleyen ve cevap yazan sohbet ajanı.

Girdi ortam değişkenleri: MESSAGE_TEXT, MESSAGE_CHAT_ID, (isteğe bağlı) REPLY_TO_TEXT.
Sadece TELEGRAM_CHAT_ID ile eşleşen sohbetten gelen mesajlar işlenir.
"""
import os
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

MAX_STEPS = 8

SYSTEM = """Sen kullanıcının kişisel takvim asistanısın; Telegram'da onunla Türkçe, kısa ve doğal konuşuyorsun.
Verilerin bir Google Sheets dosyasında. Asıl işin TAKVIM sekmesi: her günün altında o güne ait tek bir kısa not hücresi var.
Ama kullanıcı istediğinde dosyadaki HER sekmeden veri okuyabilir ve onlarda değişiklik yapabilirsin.

Bugün: {today_long} (Zürih saati).
Dosyadaki sekmeler: {tabs}

Kurallar:
- Değişiklik yapmak için araçları çağır. Aracı çağırmadan "yaptım" deme.
- TAKVIM gün notları için get_days / set_note / add_to_note / replace_text kullan. Diğer sekmeler ve TAKVIM'in başka bölümleri için list_tabs / read_range / write_cells.
- Diğer sekmelerde yazmadan önce ilgili aralığı oku, sadece istenen hücreleri değiştir, formülleri ezme (gerekirse mode='formulas' ile bak). Hangi hücre olduğu belirsizse tahmin etme, tek kısa soru sor.
- Gün notları ÇOK kısa olmalı (hücre dar): küçük harf, bir-iki kelime, mevcut stile uy ('forti', 'yana', 'forti - kocluk'). Saati sadece iş için ve kullanıcı verdiyse ekle ('14:00 forti').
- Bir güne ekleme isteniyorsa mevcut notu koru (add_to_note). Değiştirme/silme için set_note. Toplu isim düzeltmesi için replace_text.
- 'Cuma', 'haftaya salı' gibi göreli günleri bugüne göre çöz ve cevapta tarihi belirt. Tarih gerçekten belirsizse sor.
- Cevabın kısa olsun: neyi değiştirdiğini tarih/hücre ve eski -> yeni ile 1-3 satırda söyle. Sadece okuma istendiyse net cevabı ver.
- Şunları henüz yapamazsın: satır/sütun ekleme-silme, yeni sekme açma, yeni ay bloğu oluşturma. Böyle istenirse bunu dürüstçe söyle.
- Gizli bilgiyi (anahtar, token) asla yazma.

TAKVIM özeti (bugünden itibaren 21 gün):
{snapshot}"""

TR_DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")


def build_system(today, tabs, days):
    lines = []
    for k in range(22):
        d = today + timedelta(days=k)
        if d in days:
            lines.append(f"{TR_DAYS[d.weekday()]} {d.isoformat()}: {days[d] or '(boş)'}")
    return SYSTEM.format(
        today_long=f"{TR_DAYS[today.weekday()]} {today.isoformat()}",
        tabs=", ".join(tabs),
        snapshot="\n".join(lines) or "(bu aralıkta takvimde gün yok)",
    )


def run_agent(user_text, history, tools, system, generate, max_steps=MAX_STEPS):
    """tools: .declarations ve .call(name, args) sağlayan araç seti; generate: gemini.generate benzeri."""
    contents = [
        {"role": "user" if role == "user" else "model", "parts": [{"text": text}]}
        for role, text in history
    ]
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    for _ in range(max_steps):
        resp = generate(system, contents, tools.declarations)
        cand = (resp.get("candidates") or [{}])[0].get("content")
        if not cand or not cand.get("parts"):
            return "Cevap üretemedim, bir daha yazar mısın?"
        contents.append(cand)  # imzalar/düşünce parçaları dahil olduğu gibi geri gönderilir
        calls = [p["functionCall"] for p in cand["parts"] if "functionCall" in p]
        if not calls:
            return "".join(p.get("text", "") for p in cand["parts"]).strip() or "Tamam."
        results = []
        for c in calls:
            out = tools.call(c["name"], c.get("args") or {})
            if out is None:
                out = {"error": f"Bilinmeyen araç: {c['name']}"}
            results.append({"functionResponse": {"name": c["name"], "response": {"result": out}}})
        contents.append({"role": "user", "parts": results})
    return "İş çok uzadı, daha kısa parçalar hâlinde tekrar yazar mısın?"


class Toolbox:
    """Takvim ve genel sayfa araçlarını tek sette birleştirir; yapılan değişiklikleri toplar."""

    def __init__(self, *toolsets, declarations):
        self.toolsets = toolsets
        self.declarations = declarations

    def call(self, name, args):
        for ts in self.toolsets:
            out = ts.call(name, args)
            if out is not None:
                return out
        return None

    @property
    def changes(self):
        return [c for ts in self.toolsets for c in ts.changes]


def main():
    if str(os.environ.get("MESSAGE_CHAT_ID", "")) != os.environ["TELEGRAM_CHAT_ID"]:
        print("Yetkisiz sohbetten mesaj, yok sayıldı.")
        return
    text = os.environ.get("MESSAGE_TEXT", "").strip()
    if not text:
        return
    if os.environ.get("REPLY_TO_TEXT"):
        text = f"(Şu mesaja yanıt olarak: \"{os.environ['REPLY_TO_TEXT']}\")\n{text}"

    from agent import calendar_tools, gemini, memory, sheet_tools, sheets, telegram
    from agent.calendar_sheet import read_days

    telegram.send_chat_action("typing")
    now = datetime.now(ZoneInfo("Europe/Zurich"))
    log_rows = [("user", text)]
    try:
        grid = sheets.get_values("TAKVIM")
        cal = calendar_tools.CalendarTools(grid, lambda cells: sheets.update_cells("TAKVIM", cells))
        gen = sheet_tools.SheetTools(sheets)
        tools = Toolbox(
            cal, gen,
            declarations=calendar_tools.TOOL_DECLARATIONS + sheet_tools.TOOL_DECLARATIONS,
        )
        tabs = [t["title"] for t in sheets.list_tabs() if t["title"] != memory.LOG_TAB]
        system = build_system(now.date(), tabs, read_days(grid))
        history = memory.load_history(sheets)
        try:
            reply = run_agent(text, history, tools, system, gemini.generate)
        finally:
            log_rows += [("change", c) for c in tools.changes]
    except Exception:
        traceback.print_exc()
        reply = "⚠️ Bir hata oluştu, isteğin tamamlanmamış olabilir. Birazdan tekrar dener misin?"
    telegram.send_message(reply)
    log_rows.append(("bot", reply))
    try:
        memory.log(sheets, now, log_rows)
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    main()
