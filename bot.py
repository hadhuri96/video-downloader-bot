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
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import yt_dlp

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")

# سيرفر Flask خفيف لإبقاء Render شغالاً
web_app = Flask(__name__)

@web_app.route('/')
@web_app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# رسالة الترحيب
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚡ **أهلاً بك في البوت الشامل لتحميل الفيديوهات!**\n\n"
        "أرسل لي أي رابط وسأقوم بتحميله فوراً وبدون علامه مائيه:\n"
        "• **TikTok** (بدون علامة مائية ✨)\n"
        "• **Instagram** (Reels / Posts / Stories)\n"
        "• **YouTube** (Shorts / Videos)\n"
        "• **Facebook & Twitter (X)**\n\n"
        "🚀 *فقط أرسل الرابط وسأتولى الباقي!*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# التحميل المباشر عبر API Cobalt (أسرع وأضمن طريقة لتجاوز الحظر)
async def fetch_via_cobalt(url: str):
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    payload = {
        "url": url,
        "videoQuality": "max",
        "noWatermark": True
    }
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.post(api_url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") in ["tunnel", "redirect"]:
                return data.get("url")
    return None

# التعامل مع الروابط المرسلة
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح يبتدئ بـ http أو https.")
        return

    msg = await update.message.reply_text("⚡ **جاري معالجة الرابط وتحضير الفيديو...**", parse_mode='Markdown')

    # المحاولة 1: عبر API السريع (بدون علامة مائية للمنصات الشهيرة)
    try:
        direct_video_url = await fetch_via_cobalt(url)
        if direct_video_url:
            await msg.edit_text("⬆️ **جاري رفع الفيديو إلى تلجرام...**", parse_mode='Markdown')
            await update.message.reply_video(
                video=direct_video_url,
                caption="✨ **تم التحميل بنجاح وبدون علامة مائية!**"
            )
            await msg.delete()
            return
    except Exception as e:
        logging.warning(f"Cobalt API failed, switching to yt-dlp: {e}")

    # المحاولة 2: الاحتياطية عبر yt-dlp إذا فشل الـ API
    output_file = f"video_{update.message.message_id}.mp4"
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_file,
        'quiet': True,
        'max_filesize': 48 * 1024 * 1024,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

        await msg.edit_text("⬆️ **جاري رفع الفيديو إلى تلجرام...**", parse_mode='Markdown')
        with open(output_file, 'rb') as v:
            await update.message.reply_video(video=v, caption="✨ **تم التحميل بنجاح!**")

        if os.path.exists(output_file):
            os.remove(output_file)
        await msg.delete()

    except Exception as e:
        if os.path.exists(output_file):
            os.remove(output_file)
        await msg.edit_text("❌ **فشل تحميل الفيديو.**\nقد يكون الحساب خاصاً أو الفيديو يتجاوز حجم 50MB.")

def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط BOT_TOKEN!")
        return

    # تشغيل Flask
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # إعداد Event Loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    print("البوت الاحترافي الشامل يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
