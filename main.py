from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

class YouTubeChannel(BaseModel):
    channel_url: str

@app.post("/analyze")
def analyze_channel(data: YouTubeChannel):
    channel_url = data.channel_url

    # Thay YOUR_YOUTUBE_API_KEY bằng API Key thật của bạn
    API_KEY = "YOUR_YOUTUBE_API_KEY"

    # Lấy video từ kênh
    response = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_url}&maxResults=10&order=viewCount&type=video&key={API_KEY}")
    video_data = response.json()

    keywords = []
    video_results = []

    for video in video_data.get("items", []):
        title = video["snippet"]["title"]
        description = video["snippet"]["description"]
        thumbnail = video["snippet"]["thumbnails"]["high"]["url"]

        keywords += title.split()
        keywords += description.split()

        video_results.append({
            "title": title,
            "thumbnail": thumbnail
        })

    return {
        "channel": channel_url,
        "top_videos": video_results,
        "keywords": list(set(keywords))  # Loại bỏ trùng lặp
    }
