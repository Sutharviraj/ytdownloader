# 🌌 TubeGrabber | Premium Media Extractor

Modern, high-speed, and intelligent YouTube media downloader. Designed with a premium Glassmorphism UI, robust backend processing via `yt-dlp`, and complete playlist handling architecture. 

![TubeGrabber Banner](https://img.shields.io/badge/Status-Active-success.svg) ![Python](https://img.shields.io/badge/Backend-Flask_Python-blue) ![Frontend](https://img.shields.io/badge/Frontend-V3.0_Glassmorphism-purple)

---

## ✨ Key Features

- **Pristine V3.0 Architecture**: Zero-overlap CSS Grid interface with a floating responsive mobile dock.
- **Advanced Media Engineering**: Supports 1080p Video, 320kbps MP3 (Audio Extraction), and Lossless WAV format using deep FFmpeg integration.
- **Playlist & Batch Zip**: Paste a YouTube Playlist link to extract all videos simultaneously. One click compiles the result into a downloadable `.zip` file.
- **Fail-safe Engine**: Integrated intelligent fallback systems to bypass age-restrictions and metadata failures on server deployments.
- **Immersive Details**: Micro-animations, dynamic glow buttons, and iOS-inspired interface components for an incredibly premium user experience.
- **Live WebSocket/Polling Progress**: Real-time display of download speed `(MB/s)` and ETA tracking.

## 🛠️ Tech Stack
- **Backend**: Python 3, Flask, yt-dlp, UUID, threading
- **Frontend**: Custom HTML5, Vanilla JavaScript (ES6), Modern CSS3 (CSS Variables, Flex/Grid, Glassmorphism)
- **Deployment**: Render (Server), Firebase (Authentication & Analytics)

---

## 🚀 Setup & Installation (Local Development)

### Prerequisites:
1. Python 3.9+ installed on your system.
2. `FFmpeg` installed and added to your system PATH.
   - *Windows*: Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
   - *Mac*: `brew install ffmpeg`
   - *Linux*: `sudo apt install ffmpeg`

### 1. Clone the repository
```bash
git clone https://github.com/Sutharviraj/ytdownloader.git
cd ytdownloader
```

### 2. Install Python Dependencies
It is recommended to use a virtual environment.
```bash
pip install -r requirements.txt
```
*(If `requirements.txt` is missing, manually run `pip install Flask flask-cors yt-dlp imageio-ffmpeg`)*

### 3. Add Context & Cookies (Optional but Recommended)
For downloading age-restricted videos or bypassing strict YouTube bot detection on the server:
- Generate a `cookies.txt` from your Google account using a browser extension (e.g., "Get cookies.txt LOCALLY").
- Place the `cookies.txt` file in the root directory.

### 4. Run the Dev Server
```bash
python app.py
```
Open your browser and navigate to: **`http://localhost:5000`**

---

## 🌐 Production Deployment (Render)

1. Create a **Web Service** on Render.com connected to your GitHub repo.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `gunicorn app:app` (Make sure `gunicorn` is in `requirements.txt`)
4. **Environment Variables**:
   - Add `YT_COOKIES` as a Secret File or Environment Variable containing your `cookies.txt` data to prevent deployment IP blocks.

---

## 👥 Developers
- **Architecture & Full-Stack Development**: Viraj Suthar
- **Focus**: Building high-performance media tools that bridge the gap between AI and human creativity. Designed for professionals, accessible to all.

---

*Disclaimer: This tool is intended for personal use and downloading royalty-free or your own copyrighted materials. Please respect the YouTube Terms of Service.*
