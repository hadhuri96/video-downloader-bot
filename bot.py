import os
import logging
import asyncio
from threading import Thread
from flask import Flask
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# 1. إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")

# ضع هنا رابط GitHub Pages الخاص بك بعد رفعه (مثال: https://username.github.io/repo-name/)
WEB_APP_URL = "https://hadhuri96.github.io/video-downloader-bot"

# 2. سيرفر Flask خفيف لإبقاء الاستضافة (Render) شغالاً بدون توقف
web_app = Flask(__name__)

@web_app.route('/')
@web_app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# 3. أمر الترحيب (/start) مع زر Mini App
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                text="🚀 فتح أداة التنزيل المباشر", 
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "⚡ **أهلاً بك في بوت التحميل الفوري!**\n\n"
        "يمكنك استخدام الأداة السريعة عبر الزر أدناه، أو إرسال الرابط مباشرة في المحادثة:\n"
        "• **TikTok** (بدون علامة مائية ✨)\n"
        "• **Instagram Reels & Posts**\n"
        "• **YouTube Shorts**\n\n"
        "👇 اضغط على الزر لفتح الواجهة التفاعلية أو أرسل رابطك مباشرة:"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# 4. محرك استخراج رابط TikTok المباشر بدون كابتشا (TikWM API)
async def fetch_tiktok_direct(url: str):
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.post("https://www.tikwm.com/api/", data={"url": url})
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("play")
    return None

# 5. محرك عام احتياطي وسريع لبقية المنصات (VKR / Cobalt API)
async def fetch_generic_direct(url: str):
    api_url = f"https://api.vkrdown.com/v1/videodownloader?url={url}"
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(api_url)
        if response.status_code == 200:
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0].get("url")
    return None

# 6. معالجة الروابط المرسلة في المحادثة
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح يبتدئ بـ http أو https.")
        return

    msg = await update.message.reply_text("⏳ **جاري جلب الفيديو مباشرة...**", parse_mode='Markdown')

    video_url = None

    # التجربة عبر محرك تيك توك المباشر
    if "tiktok.com" in url:
        try:
            video_url = await fetch_tiktok_direct(url)
        except Exception as e:
            logging.error(f"TikTok Direct API error: {e}")

    # إذا لم يكن تيك توك أو فشل المحرك الأول، الانتقال للمحرك الشامل
    if not video_url:
        try:
            video_url = await fetch_generic_direct(url)
        except Exception as e:
            logging.error(f"Generic Direct API error: {e}")

    # إرسال الفيديو مباشرة داخل المحادثة
    if video_url:
        try:
            await msg.edit_text("⬆️ **جاري إرسال الفيديو...**", parse_mode='Markdown')
            await update.message.reply_video(
                video=video_url,
                caption="✨ **تم التحميل بنجاح وبدون علامة مائية!**"
            )
            await msg.delete()
        except Exception as e:
            await msg.edit_text("❌ حدث خطأ أثناء إرسال ملف الفيديو إلى تلجرام.")
    else:
        await msg.edit_text("❌ **فشل جلب الفيديو.** يمكنك تجربة فتح **أداة التنزيل المباشر** عبر زر /start.")

# 7. التشغيل الرئيسي للبوت
def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط متغير BOT_TOKEN!")
        return

    # تشغيل سيرفر Flask في الخلفية
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # إعداد Event Loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    print("البوت الاحترافي المباشر يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
