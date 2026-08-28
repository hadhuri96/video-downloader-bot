import os
import logging
import asyncio
from threading import Thread
from flask import Flask
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

# سيرفر Flask لإرضاء Render
web_app = Flask(__name__)

@web_app.route('/')
@web_app.route('/health')
def health_check():
    return "Bot is running perfectly!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# رسالة الترحيب الشاملة والاحترافية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **أهلاً بك في بوت التحميل الشامل والأسرع!**\n\n"
        "أرسل لي أي رابط من المنصات التالية وسأقوم بمعالجته فوراً:\n"
        "🔹 **TikTok** (بدون علامة مائية)\n"
        "🔹 **Instagram** (Reels / Posts)\n"
        "🔹 **YouTube** (Videos / Shorts)\n"
        "🔹 **Facebook & Twitter (X)**\n\n"
        "💡 *يمكنك أيضاً تحويل أي فيديو إلى مقطع صوتي MP3 بنقرة واحدة.*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# استقبال الرابط وتوفير خيارات التحميل
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح يبدأ بـ http أو https.")
        return

    msg = await update.message.reply_text("🔍 **جاري فحص الرابط واستخراج المعلومات...**", parse_mode='Markdown')

    # إعدادات yt-dlp المتطورة لتجاوز حظر تيك توك وتسهيل الروابط المختصرة
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False))
        
        title = info.get('title', 'فيديو بدون عنوان')
        duration = info.get('duration', 0)
        uploader = info.get('uploader', 'غير معروف')

        # حفظ البيانات في جلسة المستخدم
        context.user_data['download_url'] = url
        context.user_data['title'] = title

        keyboard = [
            [
                InlineKeyboardButton("🎬 تحميل الفيديو (MP4)", callback_data="dl_video"),
                InlineKeyboardButton("🎵 تحميل الصوت (MP3)", callback_data="dl_audio"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        caption_text = (
            f"📌 **العنوان:** {title[:60]}...\n"
            f"👤 **المؤلف:** {uploader}\n"
            f"⏱️ **المدة:** {duration} ثانية\n\n"
            "👇 **اختر بصيغة التحميل المطلوبة:**"
        )

        await msg.edit_text(caption_text, parse_mode='Markdown', reply_markup=reply_markup)

    except Exception as e:
        logging.error(f"Error extracting info: {e}")
        await msg.edit_text("❌ **فشل في استخراج تفاصيل الرابط.**\nتأكد أن الحساب ليس خاصاً أو أن الرابط مدعوم.")

# التعامل مع الضغط على الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get('download_url')
    if not url:
        await query.edit_message_text("❌ انتهت صلاحية الجلسة، يرجى إعادة إرسال الرابط.")
        return

    choice = query.data
    output_file = f"file_{query.message.message_id}"

    if choice == "dl_video":
        await query.edit_message_text("⏳ **جاري تحميل الفيديو برابط مباشر...**")
        output_file += ".mp4"
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_file,
            'quiet': True,
            'max_filesize': 48 * 1024 * 1024,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    else:
        await query.edit_message_text("⏳ **جاري استخراج وتحميل المقطع الصوتي...**")
        output_file += ".mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_file,
            'quiet': True,
            'max_filesize': 48 * 1024 * 1024,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

        await query.edit_message_text("⬆️ **جاري الرفع إلى تلجرام...**")

        if choice == "dl_video":
            with open(output_file, 'rb') as v:
                await query.message.reply_video(video=v, caption="✨ تم التحميل بنجاح عبر البوت الخاص بك!")
        else:
            with open(output_file, 'rb') as a:
                await query.message.reply_audio(audio=a, caption="🎵 تم استخراج الصوت بنجاح!")

        if os.path.exists(output_file):
            os.remove(output_file)
        await query.delete_message()

    except Exception as e:
        if os.path.exists(output_file):
            os.remove(output_file)
        await query.edit_message_text("❌ **حدث خطأ أثناء التحميل.** قد يتجاوز الحجم المسموح (50MB) أو الحساب مغلق.")

def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط BOT_TOKEN!")
        return

    # تشغيل سيرفر Web
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # إعداد Event Loop لـ Python 3.14
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("البوت الاحترافي يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
