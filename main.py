from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import re
from collections import Counter
import json

app = FastAPI()

# Thay API_KEY bằng API Key thực tế của bạn
API_KEY = "YOUR_YOUTUBE_API_KEY"

# Định nghĩa các dạng URL kênh YouTube
YOUTUBE_URL_PATTERNS = [
    r"youtube\.com/channel/([a-zA-Z0-9_-]+)",  # Dạng /channel/ID
    r"youtube\.com/c/([a-zA-Z0-9_-]+)",        # Dạng /c/TênKênh
    r"youtube\.com/@([a-zA-Z0-9_-]+)"          # Dạng @TênKênh
]

# Lớp định nghĩa dữ liệu đầu vào
class YouTubeChannel(BaseModel):
    channel_url: str

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
        if "items" in response and response["items"]:
            return response["items"][0]["id"]
    
    return None

# Hàm lấy video từ kênh
def get_channel_videos(channel_id: str):
    url = f"https://www.googleapis.com/youtube/v3/search?key={API_KEY}&channelId={channel_id}&part=snippet&type=video&maxResults=20"
    response = requests.get(url).json()

    if "items" not in response:
        return []

    videos = []
    for item in response["items"]:
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        videos.append({"title": title, "videoId": video_id, "url": video_url})

    return videos

# Hàm lấy lượt xem video
def get_video_views(video_id: str):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={API_KEY}"
    response = requests.get(url).json()

    if "items" in response and response["items"]:
        return int(response["items"][0]["statistics"]["viewCount"])
    
    return 0

# Hàm trích xuất từ khóa
def extract_keywords(video_titles):
    words = []
    for title in video_titles:
        words.extend(re.findall(r'\b\w+\b', title.lower()))

    word_counts = Counter(words)
    primary_keywords = word_counts.most_common(10)  # 10 từ khóa chính
    secondary_keywords = word_counts.most_common(20)[10:20]  # 10 từ khóa phụ
    extended_keywords = word_counts.most_common(30)[20:30]  # 10 từ khóa mở rộng

    return primary_keywords, secondary_keywords, extended_keywords

# API chính để phân tích kênh YouTube
@app.post("/analyze")
def analyze_channel(data: YouTubeChannel):
    channel_id = get_channel_id(data.channel_url)
    if not channel_id:
        raise HTTPException(status_code=400, detail="Không tìm thấy Channel ID")

    videos = get_channel_videos(channel_id)
    if not videos:
        raise HTTPException(status_code=400, detail="Không tìm thấy video nào")

    for video in videos:
        video["views"] = get_video_views(video["videoId"])

    avg_views = sum(v["views"] for v in videos) / len(videos) if videos else 0
    primary_keywords, secondary_keywords, extended_keywords = extract_keywords([v["title"] for v in videos])

    return {
        "channel": data.channel_url,
        "total_videos": len(videos),
        "average_views": avg_views,
        "top_videos": videos,
        "primary_keywords": primary_keywords,
        "secondary_keywords": secondary_keywords,
        "extended_keywords": extended_keywords
    }
