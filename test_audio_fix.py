import requests
import time

BASE_URL = "http://localhost:5000"
TEST_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ" # Short video (test)

def test_audio_download():
    print(f"Testing Audio Download (MP3 320kbps) for: {TEST_URL}")
    
    # 1. Trigger Download
    res = requests.post(f"{BASE_URL}/api/download", json={
        "url": TEST_URL,
        "format": "Audio",
        "format_id": "mp3_320"
    })
    
    if res.status_code != 200:
        print("Failed to trigger download")
        return
    
    task_id = res.json().get('task_id')
    print(f"Task ID: {task_id}")
    
    # 2. Poll Status
    status = ""
    while status != "Download Ready!":
        res = requests.get(f"{BASE_URL}/api/status/{task_id}")
        data = res.json()
        status = data.get('status_msg')
        finished = data.get('finished')
        error = data.get('error')
        
        print(f"Status: {status} | Progress: {data.get('progress')}%")
        
        if error:
            print(f"Error during download: {status}")
            return
        
        if finished:
            break
            
        time.sleep(1)
        
    # 3. Check Result
    filename = data.get('filename', '')
    print(f"Finished. Filename: {filename}")
    
    if filename.endswith('.mp3'):
        print("SUCCESS: File is an MP3!")
    else:
        print(f"FAILURE: Expected MP3, got {filename}")

if __name__ == "__main__":
    try:
        test_audio_download()
    except Exception as e:
        print(f"Connection failed: {e}. Is the server running?")
