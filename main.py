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
    r"youtube\.com/c/([a-zA-Z0-9_-]+)",        # Dạng /c/TênKênh
    r"youtube\.com/@([a-zA-Z0-9_-]+)",         # Dạng @TênKênh
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
        if "items" in response and response["items"]:
            return response["items"][0]["id"]

    return None

# Định nghĩa dữ liệu đầu vào
class YouTubeChannel(BaseModel):
    channel_url: str

# Hàm lấy danh sách video từ kênh
def get_videos(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/search?key={API_KEY}&channelId={channel_id}&part=snippet&type=video&maxResults=20"
    response = requests.get(url).json()

    if "items" not in response:
        return []

    videos = []
    for item in response["items"]:
        videos.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "description": item["snippet"].get("description", ""),
            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"]
        })
    return videos

# Hàm trích xuất từ khóa từ tiêu đề và mô tả
def extract_keywords(videos):
    word_counts = Counter()
    for video in videos:
        text = f"{video['title']} {video['description']}".lower()
        words = re.findall(r'\b[a-zA-Z0-9]+\b', text)
        word_counts.update(words)

    keywords = [word for word, count in word_counts.items() if count > 1]  # Chỉ lấy từ xuất hiện >1 lần
    main_keywords = keywords[:10]  # Từ khóa chính (top 10 từ phổ biến)
    sub_keywords = [word for word in keywords if word not in main_keywords]  # Từ khóa phụ
    phrase_keywords = [" ".join(words[i:i+3]) for i in range(len(words)-2)]  # Cụm từ khóa 3 từ
    return main_keywords, sub_keywords, phrase_keywords[:10]

# Hàm kiểm tra xu hướng từ khóa trên Google Trends
def check_google_trends(keyword):
    trends_url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=-180&req={{'comparisonItem':[{{'keyword':'{keyword}','geo':'','time':'today 12-m'}}],'category':0,'property':''}}"
    response = requests.get(trends_url)
    return response.status_code == 200  # Giả sử nếu trả về 200 là có xu hướng

# Hàm đề xuất tiêu đề SEO mạnh nhất
def suggest_seo_title(main_keywords):
    return f"{' '.join(main_keywords[:5])} - Bí quyết tối ưu SEO YouTube"

@app.post("/analyze")
def analyze_channel(data: YouTubeChannel):
    channel_id = get_channel_id(data.channel_url)
    if not channel_id:
        raise HTTPException(status_code=400, detail="Không thể lấy Channel ID từ URL. Vui lòng kiểm tra lại.")

    videos = get_videos(channel_id)
    if not videos:
        raise HTTPException(status_code=500, detail="Không thể lấy danh sách video từ API YouTube.")

    main_keywords, sub_keywords, phrase_keywords = extract_keywords(videos)
    trending_keywords = [kw for kw in main_keywords if check_google_trends(kw)]

    return {
        "channel": data.channel_url,
        "total_videos": len(videos),
        "top_videos": videos,
        "main_keywords": main_keywords,
        "sub_keywords": sub_keywords,
        "phrase_keywords": phrase_keywords,
        "trending_keywords": trending_keywords,
        "suggested_seo_title": suggest_seo_title(main_keywords)
    }
