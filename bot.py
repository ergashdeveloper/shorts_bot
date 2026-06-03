import os
import logging
import tempfile
import asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# === SOZLAMALAR ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def is_youtube_url(url):
    patterns = [
        r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+',
        r'(https?://)?(www\.)?youtube\.com/shorts/.+',
    ]
    return any(re.match(p, url) for p in patterns)

def is_instagram_url(url):
    return 'instagram.com' in url


async def download_video(url: str, temp_dir: str) -> str:
    """Videoni yuklab olish"""
    ydl_opts = {
        'format': 'best[filesize<50M]/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'cookiefile': None,
    }

    loop = asyncio.get_event_loop()

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename

    filename = await loop.run_in_executor(None, _download)
    return filename


# === KOMANDALAR ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Video Yuklovchi Bot\n\n"
        "Qo'llab-quvvatlanadigan platformalar:\n"
        "▶️ YouTube (video, shorts)\n"
        "📸 Instagram (reels, post)\n\n"
        "Foydalanish:\n"
        "Shunchaki video havolasini yuboring!\n\n"
        "⚠️ Maksimal hajm: 50MB"
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

    # URL tekshirish
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

            # Fayl hajmini tekshirish (50MB limit)
            file_size = os.path.getsize(filename)
            if file_size > 50 * 1024 * 1024:
                await msg.edit_text("❌ Video hajmi 50MB dan katta! Qisqaroq video yuboring.")
                return

            await msg.edit_text("📤 Telegram ga yuborilmoqda...")

            with open(filename, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                )

            await msg.delete()

    except Exception as e:
        logger.error(f"Xato: {e}")
        error_msg = str(e)
        if "Private" in error_msg or "login" in error_msg.lower():
            await msg.edit_text("❌ Bu video private! Faqat ochiq videolarni yuklab olish mumkin.")
        elif "filesize" in error_msg.lower() or "too large" in error_msg.lower():
            await msg.edit_text("❌ Video hajmi juda katta!")
        else:
            await msg.edit_text(f"❌ Yuklab bo'lmadi. Boshqa havolani sinab ko'ring.")


# === ISHGA TUSHIRISH ===

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
