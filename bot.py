import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# إعداد السجلات (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# استدعاء التوكن من متغيرات البيئة (سنضيفه في موقع الاستضافة للأمان)
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك في بوت تحميل الفيديوهات! 🎬\n\n"
        "أرسل لي رابط الفيديو من (يوتيوب، إنستغرام، فيسبوك، تيك توك، سناب شات) وسأقوم بتحميله لك فوراً."
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # التأكد من أن الرسالة تحتوي على رابط
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("يرجى إرسال رابط صحيح يبتدئ بـ http أو https.")
        return

    msg = await update.message.reply_text("⏳ جاري معالجة الرابط وتحميل الفيديو...")

    output_file = f"video_{update.message.message_id}.mp4"

    # خيارات مكتبة yt-dlp
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_file,
        'quiet': True,
        'max_filesize': 48 * 1024 * 1024, # حد أقصى 48 ميجابايت لتجنب قيود التلجرام للبوتات العادية
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await msg.edit_text("⬆️ جاري رفع الفيديو إلى تلجرام...")
        
        with open(output_file, 'rb') as video:
            await update.message.reply_video(video=video, caption="تم التحميل بنجاح ✨")

        # حذف الملف من السيرفر بعد الإرسال لتوفير المساحة
        if os.path.exists(output_file):
            os.remove(output_file)
            
        await msg.delete()

    except Exception as e:
        if os.path.exists(output_file):
            os.remove(output_file)
        await msg.edit_text(f"❌ حدث خطأ أثناء التحميل: قد يكون الرابط غير مدعوم أو أن حجم الفيديو يتجاوز الحد المسموح (50MB).")

def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط BOT_TOKEN!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
