import yt_dlp
import requests
from io import BytesIO


async def download_video(url: str) -> BytesIO:
    """
    Downloads a video from the given URL and returns it as an in-memory bytes buffer.

    Args:
        url (str): The URL of the video to download (YouTube or other supported platforms)

    Returns:
        BytesIO: In-memory file-like object containing the downloaded video

    Raises:
        Exception: If any error occurs during the download process
        requests.exceptions.RequestException: If there's an error fetching the video content
        yt_dlp.utils.DownloadError: If video download fails

    Notes:
        - Uses yt-dlp for video extraction and requests for downloading
        - Limits video size to 50MB (50 * 1024 * 1024 bytes)
        - Prioritizes MP4 format for best compatibility
        - Returns buffer with position reset to 0 for immediate reading
    """

    # Initialize in-memory binary buffer to store the video
    buffer = BytesIO()

    # YouTube-DL configuration options
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Prefer MP4 format
        'quiet': True,  # Suppress console output
        'no_warnings': True,  # Hide warning messages
        'outtmpl': '-',  # Output to stdout (captured in memory)
        'merge_output_format': 'mp4',  # Force MP4 container format
        'max_filesize': 50 * 1024 * 1024,  # 50MB size limit
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info and download
            info = ydl.extract_info(url, download=True)

            # Handle direct URL case (streaming download)
            if isinstance(info, dict) and 'url' in info:
                response = requests.get(info['url'], stream=True)
                response.raise_for_status()  # Raise HTTP errors if any

                # Stream video content in chunks to memory
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:  # Filter out keep-alive chunks
                        buffer.write(chunk)

            # Fallback to standard download method
            else:
                result = ydl.download([url])
                if isinstance(result, bytes):
                    buffer.write(result)

    except Exception as e:
        # Wrap all exceptions in a generic error message
        raise Exception(f"Download error: {str(e)}")

    # Reset buffer position to start before returning
    buffer.seek(0)
    return buffer