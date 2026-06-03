import os
import logging
import tempfile
import asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def is_youtube_url(url):
    return any(x in url for x in ['youtube.com', 'youtu.be'])

def is_instagram_url(url):
    return 'instagram.com' in url


async def download_video(url: str, temp_dir: str) -> str:
    ydl_opts = {
        # 50MB dan kichik eng yaxshi sifatni tanlaydi
        'format': 'best[filesize<50M]/best[filesize<100M]/worst',
        'outtmpl': os.path.join(temp_dir, 'video.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web'],
            }
        },
    }

    loop = asyncio.get_event_loop()

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            files = os.listdir(temp_dir)
            if files:
                return os.path.join(temp_dir, files[0])
            return None

    filename = await loop.run_in_executor(None, _download)
    return filename


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Video Yuklovchi Bot\n\n"
        "Qo'llab-quvvatlanadigan platformalar:\n"
        "▶️ YouTube (video, shorts)\n"
        "📸 Instagram (reels, post)\n\n"
        "Foydalanish:\n"
        "Shunchaki video havolasini yuboring!\n\n"
        "⚠️ Maksimal hajm: 50MB\n"
        "💡 Katta videolar avtomatik kichik sifatda yuklanadi"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Yordam:\n\n"
        "1. YouTube videosi: youtube.com/watch?v=...\n"
        "2. YouTube Shorts: youtube.com/shorts/...\n"
        "3. Instagram Reels: instagram.com/reel/...\n"
        "4. Instagram post: instagram.com/p/...\n\n"
        "Havolani yuboring — bot avtomatik yuklab beradi!"
    )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not (is_youtube_url(url) or is_instagram_url(url)):
        await update.message.reply_text(
            "❌ Noto'g'ri havola!\n\n"
            "YouTube yoki Instagram havolasini yuboring."
        )
        return

    msg = await update.message.reply_text("⏳ Yuklanmoqda... Kuting!")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            filename = await download_video(url, temp_dir)

            if not filename or not os.path.exists(filename):
                await msg.edit_text("❌ Video yuklab bo'lmadi!")
                return

            file_size = os.path.getsize(filename)
            size_mb = file_size / (1024 * 1024)

            if file_size > 50 * 1024 * 1024:
                await msg.edit_text(
                    f"❌ Video hajmi {size_mb:.1f}MB — juda katta!\n"
                    f"Telegram 50MB dan katta fayllarni qabul qilmaydi.\n"
                    f"Qisqaroq video yuboring."
                )
                return

            await msg.edit_text(f"📤 Yuborilmoqda... ({size_mb:.1f}MB)")

            with open(filename, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    supports_streaming=True,
                    read_timeout=180,
                    write_timeout=180,
                )

            await msg.delete()

    except Exception as e:
        logger.error(f"Xato: {e}")
        error_msg = str(e)
        if "private" in error_msg.lower() or "login" in error_msg.lower():
            await msg.edit_text("❌ Bu video private!")
        else:
            await msg.edit_text("❌ Yuklab bo'lmadi. Boshqa havolani sinab ko'ring.")


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    logger.info("🤖 Video yuklovchi bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
