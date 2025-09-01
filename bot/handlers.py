"""Video downloader bot module for Telegram using aiogram and yt-dlp.

This module handles video downloading from URLs provided by users and sending
the downloaded videos back through Telegram.
"""

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
import yt_dlp
import os
import tempfile
from io import BytesIO

# Initialize the router for handling Telegram messages
router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message) -> None:
    """Handle the /start command to greet users.

    Args:
        message: The incoming Telegram message object.
    """
    await message.answer("Hi! Send me the video link to download.")


async def download_video(url: str) -> BytesIO:
    """Download video from the given URL and return it as BytesIO buffer.

    Args:
        url: The URL of the video to download.

    Returns:
        BytesIO: Buffer containing the downloaded video data.

    Raises:
        Exception: If any error occurs during the download process.
    """
    buffer = BytesIO()

    # Configuration options for yt-dlp
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,  # Suppress output
        'no_warnings': True,  # Hide warnings
        'outtmpl': '-',  # Default output template
        'merge_output_format': 'mp4',  # Force MP4 format
        'max_filesize': 2000 * 1024 * 1024,  # 2GB limit
    }

    try:
        # Create temporary directory for download
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title)s.%(ext)s')

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info without downloading first
                info = ydl.extract_info(url, download=False)

                # Handle playlists by selecting first entry
                if 'entries' in info:
                    info = info['entries'][0]

                # Prepare filename and download video
                filename = ydl.prepare_filename(info)
                ydl.download([url])

                # Read downloaded file into buffer
                with open(filename, 'rb') as f:
                    buffer.write(f.read())

    except Exception as e:
        raise Exception(f"Loading error: {str(e)}")

    # Reset buffer position for reading
    buffer.seek(0)
    return buffer


@router.message()
async def video_handler(message: types.Message) -> None:
    """Handle incoming messages containing video URLs.

    Args:
        message: The incoming Telegram message object.
    """
    # Validate URL format
    if not message.text.startswith(('http://', 'https://')):
        await message.answer("Please send the correct link to the video.")
        return

    try:
        await message.answer("Starting to upload video...")
        # Download video to memory buffer
        video_buffer = await download_video(message.text)

        # Create Telegram-compatible file object
        video_file = BufferedInputFile(
            file=video_buffer.getvalue(),  # Get bytes from buffer
            filename="video.mp4"  # Set output filename
        )

        # Send video back to user
        await message.answer_video(video=video_file)

    except Exception as e:
        # Escape HTML special characters in error message
        error_message = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await message.answer(f"❌ Error loading video: {error_message}")