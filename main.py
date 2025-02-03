from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

class YouTubeRequest(BaseModel):
    channel_url: str

API_KEY = "YOUR_YOUTUBE_API_KEY"  # Thay bằng API Key thực tế của bạn

def get_channel_id(handle: str):
    """Chuyển YouTube handle thành Channel ID"""
    url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={handle}&key={API_KEY}"
    response = requests.get(url).json()
    return response["items"][0]["id"] if "items" in response else None

def extract_keywords_from_titles(video_titles):
    """Trích xuất từ khóa từ danh sách tiêu đề video"""
    all_words = []
    for title in video_titles:
        words = title.split()
        all_words.extend(words)
    
    # Xóa từ trùng lặp và sắp xếp theo độ phổ biến
    keyword_counts = {word: all_words.count(word) for word in set(all_words)}
    sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)

    main_keywords = [kw[0] for kw in sorted_keywords[:5]]  # 5 từ phổ biến nhất
    secondary_keywords = [kw[0] for kw in sorted_keywords[5:10]]  # 5 từ tiếp theo
    keyword_phrases = [" ".join(main_keywords[:3]), " ".join(main_keywords[2:5])]  # 2 cụm từ khóa

    return main_keywords, secondary_keywords, keyword_phrases

def check_trends_on_google(keyword):
    """Kiểm tra xu hướng từ khóa trên Google Trends"""
    trends_url = f"https://trends.google.com/trends/explore?q={keyword}"
    return trends_url

@app.post("/analyze")
def analyze_channel(request: YouTubeRequest):
    handle = request.channel_url.split("/")[-1]  # Lấy phần @RecollectionRoad từ URL
    channel_id = get_channel_id(handle)

    if not channel_id:
        return {"error": "Không tìm thấy Channel ID"}

    url = f"https://www.googleapis.com/youtube/v3/search?key={API_KEY}&channelId={channel_id}&part=snippet&type=video&maxResults=10"
    response = requests.get(url).json()
    
    video_titles = [item["snippet"]["title"] for item in response.get("items", [])]
    
    main_keywords, secondary_keywords, keyword_phrases = extract_keywords_from_titles(video_titles)

    trend_links = {kw: check_trends_on_google(kw) for kw in main_keywords}

    return {
        "channel": request.channel_url,
        "videos": video_titles,
        "main_keywords": main_keywords,
        "secondary_keywords": secondary_keywords,
        "keyword_phrases": keyword_phrases,
        "trends": trend_links
    }
import requests

def get_channel_id(channel_handle):
    api_key = "YOUR_YOUTUBE_API_KEY"
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={channel_handle}&type=channel&key={api_key}"
    
    response = requests.get(url)
    data = response.json()
    
    if "items" in data and len(data["items"]) > 0:
        return data["items"][0]["id"]["channelId"]
    return None

channel_handle = "@RecollectionRoad"
channel_id = get_channel_id(channel_handle)
print("Channel ID:", channel_id)
