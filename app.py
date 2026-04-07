import os
import time
import json
import re
import urllib.request
import requests
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from typing import Dict, Any

app = Flask(__name__)
CORS(app)

# Configuration
IS_CLOUD = os.environ.get('K_SERVICE') or os.environ.get('FUNCTIONS_NAME')
BASE_DIR = '/tmp' if IS_CLOUD else os.path.dirname(os.path.abspath(__file__))
ANALYTICS_FILE = os.path.join(BASE_DIR, "analytics.json")

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_info', methods=['POST'])
def get_info():
    url = request.json.get('url')
    if not url: return jsonify({"error": "No URL provided"}), 400
    
    try:
        # oEmbed Fallback for Single Videos natively (Zero IP Bans)
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
                }
        except Exception as e:
            return jsonify({"error": "Invalid YouTube URL or Private Video."}), 400
            
        qualities = [
            {"format_id": "1080", "label": "1080p HD Video"},
            {"format_id": "720",  "label": "720p HD Video"},
            {"format_id": "480",  "label": "480p SD Video"},
            {"format_id": "mp3", "label": "High-Quality MP3"},
            {"format_id": "wav", "label": "Lossless WAV"},
        ]
        
        return jsonify({
            "title": info.get('title', 'Unknown'),
            "thumbnail": info.get('thumbnail', ''),
            "uploader": info.get('uploader', 'Active User'),
            "formats": qualities,
            "is_playlist": False # Disabled multi-extraction logic natively in API mode
        })
    except Exception as e:
        return jsonify({"error": clean_ansi(str(e))}), 500

@app.route('/api/download', methods=['POST'])
def download():
    """
    Acts as a middleware wrapping the free, robust Cobalt API.
    Bypasses YouTube IP restrictions by outsourcing extraction.
    """
    data = request.json
    url = data.get('url')
    fmt = data.get('format', 'Video')
    quality = data.get('quality', '720p') # Default format fallback
    fmt_id = data.get('format_id', '720') # '1080', '720', '480', 'mp3', 'wav'
    user = data.get('user', 'Guest')
    
    if not url:
        return jsonify({"error": "Missing URL parameter."}), 400
        
    try:
        # Map our format choices to Cobalt parameters
        is_audio = fmt_id in ['mp3', 'wav']
        cobalt_payload = {
            "url": url,
            "vCodec": "h264", # Ensure universal compatibility
            "isAudioOnly": is_audio,
            "isNoTTWatermark": True
        }
        
        if is_audio:
            cobalt_payload["aFormat"] = fmt_id
        else:
            cobalt_payload["videoQuality"] = fmt_id
            
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        # Primary endpoint
        api_endpoints = [
            "https://api.cobalt.tools/api/json",
            "https://kj.szm.st/api/json",      # Mirror
            "https://cobalt.qwyzex.com/api/json"   # Mirror
        ]
        
        response_data = None
        for endpoint in api_endpoints:
            try:
                res = requests.post(endpoint, json=cobalt_payload, headers=headers, timeout=15)
                if res.status_code in [200, 202, 303]:
                    response_data = res.json()
                    break
            except Exception as ep_err:
                print(f"Failed to connect to {endpoint}: {ep_err}")
                continue
                
        if not response_data:
            raise Exception("All rendering pathways are currently busy. Please try again in a few moments.")
            
        status = response_data.get("status")
        
        if status == "error":
            raise Exception(f"Cobalt Backend Error: {response_data.get('text', 'Format block / unknown')}")
            
        download_url = response_data.get("url")
        if not download_url:
            raise Exception("Did not receive an extraction payload from the conversion server.")
            
        # Logging success via Analytics
        analytics = load_analytics()
        analytics["total_downloads"] += 1
        analytics["history"].append({
            "title": data.get('title', 'API Extracted Media'),
            "url": url,
            "timestamp": time.ctime(),
            "user": user,
            "ip": "Protected"
        })
        save_analytics(analytics)
        
        return jsonify({
            "status": "success",
            "download_url": download_url,
            "message": "Media ready!"
        })
        
    except Exception as e:
        return jsonify({"error": clean_ansi(str(e))}), 500

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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
