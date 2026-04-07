import os
import threading
import uuid
import time
import json
import zipfile
import re
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import yt_dlp
import imageio_ffmpeg
from typing import Dict, Any, List

app = Flask(__name__)
CORS(app)

# Configuration - Use /tmp for writable storage in serverless environments
IS_CLOUD = os.environ.get('K_SERVICE') or os.environ.get('FUNCTIONS_NAME')
BASE_DIR = '/tmp' if IS_CLOUD else os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
ANALYTICS_FILE = os.path.join(BASE_DIR, "analytics.json")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def cleanup_old_files():
    """Delete files older than 30 minutes to save space on Render."""
    now = time.time()
    for f in os.listdir(DOWNLOAD_DIR):
        fpath = os.path.join(DOWNLOAD_DIR, f)
        if os.stat(fpath).st_mtime < now - 1800:
            try:
                if os.path.isfile(fpath): os.remove(fpath)
            except: pass

@app.before_request
def before_request():
    # Run cleanup occasionally
    if time.time() % 10 < 1: # ~10% of requests
        threading.Thread(target=cleanup_old_files).start()

# Global task storage
tasks: Dict[str, Any] = {}

def load_analytics() -> Dict[str, Any]:
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except:
            pass
    return {"total_downloads": 0, "history": []}

def save_analytics(data):
    with open(ANALYTICS_FILE, 'w') as f:
        json.dump(data, f)

def clean_ansi(text):
    ansi_escape = re.compile(r'\033\[[0-9;]*[mK]')
    return ansi_escape.sub('', text)

class AdvancedWorker(threading.Thread):
    def __init__(self, task_id, url, format_type, quality, format_id=None, user_info=None):
        super().__init__()
        self.task_id = task_id
        self.url = url
        self.format_type = format_type
        self.quality = quality
        self.format_id = format_id
        self.user_info = user_info
        self.progress = 0
        self.speed = "0 MB/s"
        self.eta = "00:00"
        self.status_msg = "Initializing..."
        self.finished = False
        self.error = False
        self.final_filename = ""
        self.all_files = []
        self.total_videos = 1

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                p = d.get('_percent_str', '0%').replace('%', '').strip()
                self.progress = int(float(p))
                self.speed = d.get('_speed_str', '0 MB/s')
                self.eta = d.get('_eta_str', '00:00')
                self.status_msg = f"Downloading: {self.progress}%"
            except:
                pass
        elif d['status'] == 'finished':
            self.progress = 100
            self.status_msg = "Processing..."

    def run(self):
        url = self.url
        try:
            FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
            FFMPEG_DIR = os.path.dirname(FFMPEG_PATH)
        except:
            FFMPEG_DIR = "/usr/bin" # Standard Linux fallback
        
        # Base Options
        ydl_opts: Dict[str, Any] = {
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'logger': None,
            'ffmpeg_location': FFMPEG_DIR,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'mweb', 'android', 'web'],
                },
                'youtubetab': {
                    'skip': ['authcheck']
                }
            },
            'nocheckcertificate': True,
            'no_color': True,
            'geo_bypass': True,
            'quiet': True,
        }

        proxy_url = os.environ.get('PROXY_URL')
        if proxy_url:
            ydl_opts['proxy'] = proxy_url
            print("Using configured proxy.")

        # Cookie Support - Secure way via Environment Variable or File
        cookie_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
        cookie_env = os.environ.get('YT_COOKIES')
        
        if cookie_env and len(cookie_env) > 10:
            # Use environment variable content
            cookie_file = os.path.join(BASE_DIR, 'cookies.txt')
            try:
                with open(cookie_file, 'w') as f:
                    f.write(cookie_env)
                ydl_opts['cookiefile'] = cookie_file
                print("Using cookies from environment variable.")
            except Exception as ce:
                print(f"Failed to write cookie file from environment: {ce}")
        elif os.path.exists(cookie_path):
            # Use local file
            ydl_opts['cookiefile'] = cookie_path
            print(f"Using cookies from file: {cookie_path}")
        else:
            print("No cookies found. Using unauthenticated session (may be blocked).")

        # Specific Quality Logic
        if self.format_id:
            q = self.format_id
            if q == '1080p':
                ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best'
            elif q == '720p':
                ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best'
            elif q == '480p':
                ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best'
            elif q == 'mp3_320':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }]
            elif q == 'wav':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }]
            else:
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
        elif self.format_type == "Audio":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else: # Default Video
            ydl_opts['format'] = 'bestvideo+bestaudio/best'

        try:
            # Snapshot downloads dir BEFORE download to detect new files after
            before_files = set(os.listdir(DOWNLOAD_DIR))
            
            # Stage 1: Attempt Optimized (High Quality)
            try:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                except Exception as p_err:
                    if 'proxy' in ydl_opts and ('ProxyError' in str(p_err) or '402' in str(p_err)):
                        print("Proxy failed in Stage 1. Retrying without proxy...")
                        del ydl_opts['proxy']
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=True)
                    else:
                        raise p_err
            except Exception as e:
                # Stage 2: Guaranteed Fallback using android client
                print(f"Stage 1 failed: {e}. Using guaranteed android fallback...")
                
                # Determine if we should use audio-only for fallback
                is_audio = self.format_type == "Audio" or (self.format_id and self.format_id in ['mp3_320', 'wav'])
                
                fallback_opts = {
                    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                    'progress_hooks': [self.progress_hook],
                    'logger': None,
                    'ffmpeg_location': FFMPEG_DIR,
                    'extractor_args': {'youtube': {'player_client': ['ios', 'mweb', 'android']}},
                    'nocheckcertificate': True,
                    'no_color': True,
                    'geo_bypass': True,
                    'quiet': True,
                    'format': 'bestaudio/best' if is_audio else 'best',
                }
                
                if proxy_url:
                    fallback_opts['proxy'] = proxy_url
                
                if is_audio and 'postprocessors' in ydl_opts:
                    fallback_opts['postprocessors'] = ydl_opts['postprocessors']

                try:
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                except Exception as p_err2:
                    if 'proxy' in fallback_opts and ('ProxyError' in str(p_err2) or '402' in str(p_err2)):
                        print("Proxy failed in Stage 2. Retrying without proxy...")
                        del fallback_opts['proxy']
                        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                            info = ydl.extract_info(url, download=True)
                    else:
                        raise p_err2

            # Robust file detection: snapshot before vs after
            after_files = set(os.listdir(DOWNLOAD_DIR))
            new_files = [os.path.join(DOWNLOAD_DIR, f) for f in (after_files - before_files)
                         if not f.endswith('.part') and not f.endswith('.ytdl')]
            
            if new_files:
                # Sort by modification time, newest first
                new_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                self.all_files = new_files
                self.final_filename = new_files[0]
                self.total_videos = len(new_files)
            elif info.get('_type') == 'playlist':
                self.total_videos = len(info.get('entries', []))

            self.status_msg = "Download Ready!"
        except Exception as e:
            self.error = True
            err_msg = str(e)
            if "Requested format is not available" in err_msg:
                self.status_msg = "Error: This specific quality is not available for this video. Try '720p' or 'Auto'."
            elif "Sign in to confirm your age" in err_msg:
                self.status_msg = "Error: This video is age-restricted and cannot be downloaded."
            else:
                clean_err = clean_ansi(err_msg)
                if "Sign in to confirm you're not a bot" in clean_err:
                    self.status_msg = "Error: YouTube is blocking this server IP. (Owner: Please provide valid cookies.txt to bypass)."
                elif "Sign in to confirm your age" in clean_err:
                    self.status_msg = "Error: This video is age-restricted. Cookies are required to download."
                else:
                    self.status_msg = f"Failed: {clean_err[:100]}..."

        self.finished = True
        
        if not self.error:
            analytics = load_analytics()
            analytics["total_downloads"] += 1
            analytics["history"].append({
                "title": os.path.basename(self.final_filename),
                "url": self.url,
                "timestamp": time.ctime(),
                "user": self.user_info.get('email', 'Guest') if self.user_info else "Guest",
                "ip": "Protected"
            })
            save_analytics(analytics)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_info', methods=['POST'])
def get_info():
    url = request.json.get('url')
    if not url: return jsonify({"error": "No URL provided"}), 400
    
    try:
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    except:
        FFMPEG_PATH = "/usr/bin/ffmpeg"
        
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True,
        'extract_flat': 'in_playlist',  # Speeds up playlist parsing heavily
        'skip_download': True,
        'ffmpeg_location': FFMPEG_PATH,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'mweb', 'android', 'web']
            },
            'youtubetab': {
                'skip': ['authcheck']
            }
        }
    }

    proxy_url = os.environ.get('PROXY_URL')
    if proxy_url:
        ydl_opts['proxy'] = proxy_url

    cookie_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
    cookie_env = os.environ.get('YT_COOKIES')
    if cookie_env and len(cookie_env) > 10:
        cookie_file = os.path.join(os.path.dirname(__file__), 'cookies.txt')
        try:
            with open(cookie_file, 'w') as f:
                f.write(cookie_env)
            ydl_opts['cookiefile'] = cookie_file
        except: pass
    elif os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
        
    try:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as proxy_err:
            if 'proxy' in ydl_opts and ('ProxyError' in str(proxy_err) or '402' in str(proxy_err)):
                print("Proxy failed during get_info. Retrying without proxy...")
                del ydl_opts['proxy']
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                except:
                    info = None
            else:
                info = None
                
        # FAIL-SAFE oEmbed Fallback for Single Videos
        if info is None:
            print("yt-dlp blocked. Attempting oEmbed fallback...")
            import urllib.request
            try:
                oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
                req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    info = {
                        'title': data.get('title', 'YouTube Video'),
                        'thumbnail': data.get('thumbnail_url', ''),
                        'uploader': data.get('author_name', 'YouTube Channel'),
                        '_type': 'video'
                    }
            except Exception as e:
                print("oEmbed fallback also failed:", e)
                raise Exception("YouTube is actively blocking this server's IP address. Please wait or use valid cookies.")
            
        qualities = [
            {"format_id": "1080p", "label": "1080p HD"},
            {"format_id": "720p",  "label": "720p HD"},
            {"format_id": "480p",  "label": "480p SD"},
            {"format_id": "mp3_320", "label": "320kbps MP3"},
            {"format_id": "wav",    "label": "Lossless WAV"},
        ]
        
        is_playlist = info.get('_type') == 'playlist'
        
        return jsonify({
            "title": info.get('title', 'Unknown'),
            "thumbnail": info.get('thumbnail', ''),
            "uploader": info.get('uploader', 'Active User'),
            "formats": qualities,
            "is_playlist": is_playlist
        })
    except Exception as e:
        return jsonify({"error": clean_ansi(str(e))}), 500

@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    fmt = data.get('format', 'Video')
    quality = data.get('quality', '720p')
    fmt_id = data.get('format_id')
    user = data.get('user')

    task_id = str(uuid.uuid4())
    worker = AdvancedWorker(task_id, url, fmt, quality, fmt_id, user)
    tasks[task_id] = worker
    worker.start()
    
    return jsonify({"task_id": task_id})

@app.route('/api/status/<task_id>')
def status(task_id):
    worker = tasks.get(task_id)
    if not worker: return jsonify({"error": "Task not found"}), 404
    
    return jsonify({
        "progress": worker.progress,
        "status_msg": worker.status_msg,
        "speed": worker.speed,
        "eta": worker.eta,
        "finished": worker.finished,
        "error": worker.error,
        "filename": os.path.basename(worker.final_filename) if worker.final_filename else "",
        "all_files": [os.path.basename(f) for f in worker.all_files],
        "total_videos": worker.total_videos
    })

@app.route('/api/history')
def get_history():
    analytics = load_analytics()
    return jsonify(analytics["history"][-20:])

@app.route('/api/visit', methods=['POST'])
def visit():
    return jsonify({"status": "ok"})

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({"status": "awake"})

@app.route('/api/zip/<task_id>')
def get_zip(task_id):
    worker = tasks.get(task_id)
    if not worker or not worker.finished or not worker.all_files:
        return jsonify({"error": "Files not ready"}), 400
    
    zip_filename = f"playlist_{task_id}.zip"
    zip_path = os.path.join(DOWNLOAD_DIR, zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w') as z:
        for f in worker.all_files:
            if os.path.exists(f):
                z.write(f, os.path.basename(f))
    
    return jsonify({"zip_url": f"/downloads/{zip_filename}"})

@app.route('/api/get_file/<task_id>')
def get_file(task_id):
    worker = tasks.get(task_id)
    if not worker or not worker.finished or not worker.final_filename:
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(DOWNLOAD_DIR, os.path.basename(worker.final_filename), as_attachment=True)

@app.route('/downloads/<path:filename>')
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
