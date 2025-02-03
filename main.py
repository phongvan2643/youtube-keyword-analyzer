from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import re
from collections import Counter

app = FastAPI()

# Define the request model
class YouTubeChannelRequest(BaseModel):
    channel_url: str

# Function to extract Channel ID from YouTube URL
def get_channel_id(channel_url):
    api_key = "YOUR_YOUTUBE_API_KEY"  # Replace with your actual YouTube API Key
    username = channel_url.split("/")[-1]
    youtube_api_url = f"https://www.googleapis.com/youtube/v3/search?key={api_key}&q={username}&type=channel&part=id"
    
    response = requests.get(youtube_api_url)
    if response.status_code == 200:
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            return data["items"][0]["id"]["channelId"]
    return None

# Function to fetch ALL video details from a channel
def fetch_all_videos(channel_id):
    api_key = "YOUR_YOUTUBE_API_KEY"  # Replace with your actual YouTube API Key
    videos = []
    next_page_token = None

    while True:
        youtube_api_url = (
            f"https://www.googleapis.com/youtube/v3/search?key={api_key}"
            f"&channelId={channel_id}&part=snippet&type=video&maxResults=50"
            + (f"&pageToken={next_page_token}" if next_page_token else "")
        )

        response = requests.get(youtube_api_url)
        if response.status_code == 200:
            data = response.json()
            videos.extend(
                [
                    {
                        "video_id": item["id"]["videoId"],
                        "title": item["snippet"]["title"],
                        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                    }
                    for item in data.get("items", [])
                ]
            )
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        else:
            break

    return videos

# Function to extract keywords from video titles
def extract_keywords(video_titles):
    words = []
    for title in video_titles:
        words.extend(re.findall(r"\b\w+\b", title.lower()))
    
    keyword_counts = Counter(words)
    
    # Filter out common stop words
    stop_words = {"the", "in", "of", "and", "to", "a", "on", "for", "with", "is", "how", "you", "your", "this", "it", "that"}
    filtered_keywords = {k: v for k, v in keyword_counts.items() if k not in stop_words and len(k) > 2}
    
    sorted_keywords = sorted(filtered_keywords.items(), key=lambda x: x[1], reverse=True)
    
    main_keywords = [word for word, count in sorted_keywords[:10]]  # Top 10 keywords
    keyword_phrases = [
        " ".join(title.split()[i : i + 3])
        for title in video_titles
        for i in range(len(title.split()) - 2)
    ]

    return {"main_keywords": main_keywords, "keyword_phrases": keyword_phrases}

# Function to check keyword trends on Google Trends
def check_google_trends(keywords):
    trends_data = {}
    for keyword in keywords:
        trends_url = f"https://trends.google.com/trends/explore?q={keyword}"
        trends_data[keyword] = trends_url  # Placeholder (Actual scraping API may be required)

    return trends_data

# API Endpoint to analyze YouTube channel
@app.post("/analyze")
def analyze_channel(request: YouTubeChannelRequest):
    channel_id = get_channel_id(request.channel_url)
    
    if not channel_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy Channel ID.")

    videos = fetch_all_videos(channel_id)
    if not videos:
        raise HTTPException(status_code=404, detail="Không tìm thấy video nào trên kênh.")

    video_titles = [video["title"] for video in videos]
    keywords_data = extract_keywords(video_titles)
    google_trends = check_google_trends(keywords_data["main_keywords"])

    return {
        "channel": request.channel_url,
        "total_videos": len(videos),
        "top_videos": videos[:10],  # Trả về 10 video tiêu biểu
        "keywords": keywords_data,
        "google_trends": google_trends,
    }
