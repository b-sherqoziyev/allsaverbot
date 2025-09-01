import os
import asyncio
import logging
from typing import Optional, Tuple

import httpx
from dotenv import load_dotenv
from telegram import __version__ as TG_VER

# python-telegram-bot 20.x async API
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()

# ====== Config ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
COBALT_API_URL = os.getenv("COBALT_API_URL", "").rstrip("/")
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "49"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env da aniqlanmagan!")

if not COBALT_API_URL:
    raise RuntimeError("COBALT_API_URL .env da aniqlanmagan!")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cobalt-bot")

# HTTP client (async)
http_client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)


# ===== Helpers =====
def extract_first_url(text: str) -> Optional[str]:
    if not text:
        return None
    import re
    m = re.search(r"(https?://\S+)", text)
    return m.group(1) if m else None


async def cobalt_resolve(url: str, is_audio_only: bool = False) -> Tuple[str, str]:
    """
    POST {COBALT_API_URL}/api/json with url and return (direct_url, kind) where kind is 'video'|'audio'|'file'|'image'
    Raises RuntimeError on error.
    """
    api = COBALT_API_URL.rstrip("/") + "/api/json"
    payload = {
        "url": url,
        "isAudioOnly": bool(is_audio_only),
        # You can add other cobalt params if you want (vQuality, vCodec, aFormat, filenamePattern ...)
    }
    log.info("Cobalt request: %s", url)
    r = await http_client.post(api, json=payload, headers={"Accept": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"Cobalt returned HTTP {r.status_code}")
    data = r.json()
    status = data.get("status")
    if status in ("redirect", "success", "stream"):
        direct = data.get("url")
        if not direct:
            raise RuntimeError("Cobalt returned no url")
        kind = "audio" if is_audio_only else "video"
        # some instances include 'type' or 'mimetype' — try to infer
        if data.get("type") == "image" or (direct.endswith(".jpg") or direct.endswith(".png") or "image" in (data.get("mimetype") or "")):
            kind = "image"
        return direct, kind
    if status == "picker":
        picker = data.get("picker") or []
        if not picker:
            raise RuntimeError("Cobalt picker empty")
        # choose first
        direct = picker[0].get("url")
        if not direct:
            raise RuntimeError("Cobalt picker item missing url")
        kind = "audio" if is_audio_only else "video"
        return direct, kind
    # rate-limit or login-required may return status "error" with text
    text = data.get("text") or data.get("error") or "Cobalt error"
    raise RuntimeError(text)


async def get_content_length(url: str) -> Optional[int]:
    try:
        r = await http_client.head(url, timeout=20.0)
        if r.status_code >= 400:
            return None
        cl = r.headers.get("Content-Length") or r.headers.get("content-length")
        return int(cl) if cl and cl.isdigit() else None
    except Exception:
        return None


def human_mb(nbytes: int) -> str:
    return f"{nbytes / (1024*1024):.1f} MB"


# ===== Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Men Cobalt orqali media yuklab beruvchi botman.\n"
        "Foydalanish:\n"
        "• Link yuboring — video yuboraman.\n"
        "• /audio <link> — faqat audio.\n"
        "• /video <link> — videoni yuboraman.\n"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Link yuboring yoki /audio <link> /video <link>")


async def send_media_from_cobalt(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, mode: str):
    """
    mode: 'video' or 'audio'
    """
    msg = update.message
    await msg.reply_text("⏳ Cobalt orqali so‘rov yuborilmoqda...")

    is_audio = (mode == "audio")
    try:
        direct_url, kind = await cobalt_resolve(url, is_audio_only=is_audio)
    except Exception as e:
        log.exception("Cobalt error")
        await msg.reply_text(f"❌ Cobalt xatosi: {e}")
        return

    size_bytes = await get_content_length(direct_url)
    size_note = f" ({human_mb(size_bytes)})" if size_bytes else ""

    # Telegram Bot API cloud upload limit ~50MB (depends). If greater — yuborish o‘rniga link beramiz
    if size_bytes and size_bytes > MAX_FILE_MB * 1024 * 1024:
        await msg.reply_text(
            f"⚠️ Fayl hajmi {human_mb(size_bytes)} — bot orqali yuborib bo‘lmaydi.\n"
            f"To‘g‘ri yuklab olish havolasi:\n{direct_url}"
        )
        return

    caption = f"✅ Tayyor{size_note}"
    try:
        if kind == "audio" or is_audio:
            await msg.reply_audio(audio=direct_url, caption=caption)
        elif kind == "image":
            await msg.reply_photo(photo=direct_url, caption=caption)
        else:
            # video or generic file
            await msg.reply_video(video=direct_url, caption=caption)
    except Exception as e:
        log.exception("Telegram send error")
        # oxirgi chora: yuborishning imkoni bo'lmasa link yuborish
        await msg.reply_text(f"⚠️ Telegramga yuborishda muammo. Mana link: {direct_url}\nXato: {e}")


async def audio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        url = args[0]
    else:
        # maybe reply
        url = extract_first_url(update.message.reply_to_message.text) if update.message.reply_to_message else None
    if not url:
        await update.message.reply_text("Iltimos: /audio <link> yoki postga javob qilib link yuboring.")
        return
    await send_media_from_cobalt(update, context, url, mode="audio")


async def video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        url = args[0]
    else:
        url = extract_first_url(update.message.reply_to_message.text) if update.message.reply_to_message else None
    if not url:
        await update.message.reply_text("Iltimos: /video <link> yoki postga javob qilib link yuboring.")
        return
    await send_media_from_cobalt(update, context, url, mode="video")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    url = extract_first_url(text)
    if not url:
        return  # ignore non-URL messages
    await send_media_from_cobalt(update, context, url, mode="video")


# ===== App startup =====
async def on_startup(app):
    log.info("Bot started")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("audio", audio_cmd))
    app.add_handler(CommandHandler("video", video_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
