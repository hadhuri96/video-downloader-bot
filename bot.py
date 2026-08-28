import os
import logging
import asyncio
from threading import Thread
from flask import Flask
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
        "أرسل لي أي رابط من:\n"
        "• **TikTok** (بدون علامة مائية ✨)\n"
        "• **YouTube Shorts / Videos**\n"
        "• **Instagram Reels**\n\n"
        "🚀 *فقط قم بإرسال الرابط وسأقوم بتنزيله فوراً!*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# API متطور لتنزيل تيك توك بدون علامة مائية
async def download_tiktok(url: str):
    api_url = f"https://api.tiklydown.eu.org/api/download?url={url}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(api_url)
        if response.status_code == 200:
            data = response.json()
            # استخراج رابط الفيديو المباشر بدون علامة مائية
            video_url = data.get("video", {}).get("noWatermark") or data.get("video", {}).get("watermark")
            return video_url
    return None

# API متطور عام للروابط الأخرى (Shorts / Reels)
async def download_generic(url: str):
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    payload = {"url": url, "videoQuality": "720"}
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        res = await client.post(api_url, json=payload, headers=headers)
        if res.status_code == 200:
            data = res.json()
            return data.get("url")
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
        return

    msg = await update.message.reply_text("⏳ **جاري جلب الفيديو...**", parse_mode='Markdown')

    video_url = None

    # المعالجة الخاصة بتيك توك
    if "tiktok.com" in url:
        try:
            video_url = await download_tiktok(url)
        except Exception as e:
            logging.error(f"TikTok API error: {e}")

    # إذا لم يكن تيك توك أو فشل المحرك الأول، استخدم المحرك العام
    if not video_url:
        try:
            video_url = await download_generic(url)
        except Exception as e:
            logging.error(f"Generic API error: {e}")

    # إرسال الفيديو للمستخدم
    if video_url:
        try:
            await msg.edit_text("⬆️ **جاري الرفع إلى تلجرام...**", parse_mode='Markdown')
            await update.message.reply_video(
                video=video_url,
                caption="✨ **تم التحميل بنجاح!**\n\nتم التنزيل عبر البوت الخاص بك."
            )
            await msg.delete()
        except Exception as e:
            await msg.edit_text("❌ حدث خطأ أثناء إرسال الفيديو، قد يكون حجمه كبيراً جداً.")
    else:
        await msg.edit_text("❌ **فشل التحميل.** الرابط غير مدعوم أو أن السيرفر المحمل عليه مشغولات حالياً.")

def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط BOT_TOKEN!")
        return

    # تشغيل Flask
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # تهيئة Event Loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("البوت يعمل بنجاح...")
    app.run_polling()

if __name__ == '__main__':
    main()
