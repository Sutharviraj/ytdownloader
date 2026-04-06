import yt_dlp
import os
import sys

# Current configuration from app.py
DOWNLOAD_DIR = r"c:\Users\arvind\.gemini\antigravity\scratch\ytdownloader\downloads"
FFMPEG_DIR = r"c:\Users\arvind\.gemini\antigravity\scratch\ytdownloader"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ" # Test video

ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
    'ffmpeg_location': FFMPEG_DIR,
    'restrictfilenames': True,
    'quiet': False,
    'no_warnings': False,
}

print(f"Testing with FFMPEG_DIR: {FFMPEG_DIR}")
print(f"Testing with DOWNLOAD_DIR: {DOWNLOAD_DIR}")

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        print("SUCCESS! File should be in downloads folder.")
        filepath = ydl.prepare_filename(info)
        print(f"Expected path: {filepath}")
        if os.path.exists(filepath):
            print("Verified: File exists!")
        else:
            # Check for merged files or post-processed files
            for f in os.listdir(DOWNLOAD_DIR):
                print(f"Found in downloads: {f}")
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
