import os
import logging
import asyncio
from threading import Thread
from flask import Flask
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")

# سيرفر Flask مصغر لمنع توقف Render
web_app = Flask(__name__)

@web_app.route('/')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚡ **أهلاً بك في بوت التحميل السريع!**\n\n"
        "أرسل لي أي رابط وسأقوم بتحميله فوراً:\n"
        "• **TikTok** (بدون علامة مائية ✨)\n"
        "• **YouTube Shorts / Videos**\n"
        "• **Instagram Reels**\n\n"
        "🚀 *أرسل الرابط الآن ليستخرج البوت الفيديو لك.*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# السيرفر الأول: TikWm (مخصص لـ TikTok بدون علامة مائية)
async def fetch_tikwm(url: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post("https://www.tikwm.com/api/", data={"url": url})
        if res.status_code == 200:
            data = res.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("play")
    return None

# السيرفر الثاني: Rapid/Social API (لجميع المنصات)
async def fetch_lovesocial(url: str):
    api_url = f"https://api.vkrdown.com/v1/videodownloader?url={url}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(api_url)
        if res.status_code == 200:
            data = res.json()
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0].get("url")
    return None

# السيرفر الثالث: Cobalt API (سيرفر احتياطي عام)
async def fetch_cobalt(url: str):
    api_url = "https://co.wuk.sh/api/json"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {"url": url}
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(api_url, json=payload, headers=headers)
        if res.status_code == 200:
            return res.json().get("url")
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح يبتدئ بـ http أو https.")
        return

    msg = await update.message.reply_text("⏳ **جاري معالجة الرابط من السيرفرات المخصصة...**", parse_mode='Markdown')

    video_url = None

    # 1. التجربة عبر سيرفر TikTok المخصص
    if "tiktok.com" in url:
        try:
            video_url = await fetch_tikwm(url)
        except Exception:
            pass

    # 2. التجربة عبر سيرفر VKR الشامل إذا لم ينجح الأول
    if not video_url:
        try:
            video_url = await fetch_lovesocial(url)
        except Exception:
            pass

    # 3. التجربة عبر سيرفر Cobalt الاحتياطي
    if not video_url:
        try:
            video_url = await fetch_cobalt(url)
        except Exception:
            pass

    # إرسال الفيديو إذا تم استخراجه من أحد السيرفرات
    if video_url:
        try:
            await msg.edit_text("⬆️ **جاري رفع الفيديو إلى تلجرام...**", parse_mode='Markdown')
            await update.message.reply_video(
                video=video_url,
                caption="✨ **تم التحميل بنجاح وبدون علامة مائية!**"
            )
            await msg.delete()
        except Exception as e:
            await msg.edit_text("❌ حدث خطأ أثناء إرسال الفيديو إلى تلجرام.")
    else:
        await msg.edit_text("❌ **فشل جلب الفيديو.** الرابط قد يكون لحساب خاص أو من منصة غير مدعومة.")

def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط BOT_TOKEN!")
        return

    # تشغيل سيرفر Flask
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # إعداد Event Loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("البوت يعمل بنجاح عبر السيرفرات المخصصة...")
    app.run_polling()

if __name__ == '__main__':
    main()
