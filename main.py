import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
from collections import Counter
import json

app = FastAPI()

# Thay API_KEY bằng API Key thực tế của bạn
API_KEY = "YOUR_YOUTUBE_API_KEY"

# Định nghĩa các dạng URL kênh YouTube
YOUTUBE_URL_PATTERNS = [
    r"youtube\.com/channel/([a-zA-Z0-9_-]+)",  # Dạng /channel/ID
    r"youtube\.com/c/([a-zA-Z0-9_-]+)",  # Dạng /c/TênKênh
    r"youtube\.com/@([a-zA-Z0-9_-]+)",  # Dạng @TênKênh
]

# Hàm lấy Channel ID từ URL
def get_channel_id(channel_url: str):
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, channel_url)
        if match:
            return match.group(1)
    
    # Nếu là @username, chuyển thành Channel ID
    if "youtube.com/@" in channel_url:
        username = channel_url.split("@")[-1]
        url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={username}&key={API_KEY}"
        response = requests.get(url).json()
        if "items" in response and len(response["items"]) > 0:
            return response["items"][0]["id"]
    
    return None

# Hàm lấy danh sách video từ kênh YouTube
def get_channel_videos(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/search?key={API_KEY}&channelId={channel_id}&part=snippet&type=video&maxResults=50"
    response = requests.get(url).json()

    videos = []
    if "items" in response:
        for item in response["items"]:
            videos.append({
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "thumbnail": item["snippet"]["thumbnails"]["high"]["url"]
            })
    return videos

# Hàm trích xuất từ khóa từ tiêu đề và mô tả
def extract_keywords(videos):
    keywords = []
    for video in videos:
        text = f"{video['title']} {video['description']}"
        words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        keywords.extend(words)

    keyword_counts = Counter(keywords)
    common_keywords = keyword_counts.most_common(50)
    
    # Tách từ khóa chính, phụ, cụm từ khóa 3 từ
    primary_keywords = [kw[0] for kw in common_keywords[:10]]
    secondary_keywords = [kw[0] for kw in common_keywords[10:30]]
    phrase_keywords = [f"{w1} {w2} {w3}" for w1, w2, w3 in zip(keywords, keywords[1:], keywords[2:]) if len(set([w1, w2, w3])) == 3]

    return {
        "primary_keywords": primary_keywords,
        "secondary_keywords": secondary_keywords,
        "phrase_keywords": phrase_keywords[:20]
    }

# API phân tích kênh YouTube
class YouTubeChannel(BaseModel):
    channel_url: str

@app.post("/analyze")
def analyze_channel(data: YouTubeChannel):
    channel_id = get_channel_id(data.channel_url)
    if not channel_id:
        raise HTTPException(status_code=400, detail="Không tìm thấy Channel ID.")

    videos = get_channel_videos(channel_id)
    if not videos:
        raise HTTPException(status_code=400, detail="Không tìm thấy video nào trên kênh.")

    keywords = extract_keywords(videos)

    return {
        "channel": data.channel_url,
        "top_videos": videos[:5],  # Trả về 5 video tiêu biểu
        "keywords": keywords
    }
