import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك في بوت تحميل الفيديوهات! 🎬\n\n"
        "أرسل لي رابط الفيديو من (يوتيوب، إنستغرام، فيسبوك، تيك توك، سناب شات) وسأقوم بتحميله لك."
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("يرجى إرسال رابط صحيح يبتدئ بـ http أو https.")
        return

    msg = await update.message.reply_text("⏳ جاري معالجة الرابط وتحميل الفيديو...")
    output_file = f"video_{update.message.message_id}.mp4"

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_file,
        'quiet': True,
        'max_filesize': 48 * 1024 * 1024,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await msg.edit_text("⬆️ جاري رفع الفيديو إلى تلجرام...")
        
        with open(output_file, 'rb') as video:
            await update.message.reply_video(video=video, caption="تم التحميل بنجاح ✨")

        if os.path.exists(output_file):
            os.remove(output_file)
            
        await msg.delete()

    except Exception as e:
        if os.path.exists(output_file):
            os.remove(output_file)
        await msg.edit_text("❌ حدث خطأ أثناء التحميل: قد يكون الرابط غير مدعوم أو أن حجم الفيديو يتجاوز 50MB.")

def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط BOT_TOKEN!")
        return

    t = Thread(target=run_health_check_server)
    t.daemon = True
    t.start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
