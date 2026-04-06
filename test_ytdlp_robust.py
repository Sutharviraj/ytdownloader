import yt_dlp
import os

DOWNLOAD_DIR = r"c:\Users\arvind\.gemini\antigravity\scratch\ytdownloader\downloads"
FFMPEG_DIR = r"c:\Users\arvind\.gemini\antigravity\scratch\ytdownloader"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"

ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
    'ffmpeg_location': FFMPEG_DIR,
    'restrictfilenames': True,
    'quiet': False,
    'no_warnings': False,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'referer': 'https://www.google.com/',
    'http_headers': {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
    }
}

print("Running ROBUST test...")
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        print("SUCCESS!")
except Exception as e:
    print(f"FAILED: {str(e)}")
