from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import re
from collections import Counter
import pandas as pd

app = FastAPI()

# ✅ Fix lỗi 405 bằng cách hỗ trợ cả HEAD request
@app.get("/", include_in_schema=False)
@app.head("/")
def home():
    return {"message": "YouTube Keyword Analyzer API is running!"}

# ✅ Fix lỗi 405 bằng cách hỗ trợ HEAD request cho Swagger UI
@app.get("/docs", include_in_schema=False)
@app.head("/docs")
def docs_redirect():
    return {"message": "OpenAPI docs are available at /docs"}

# Định nghĩa dữ liệu đầu vào
class YouTubeChannel(BaseModel):
    channel_url: str

# Định nghĩa các dạng URL hợp lệ của YouTube
YOUTUBE_URL_PATTERNS = [
    r"youtube\.com/channel/([a-zA-Z0-9_-]+)",  
    r"youtube\.com/c/([a-zA-Z0-9_-]+)",        
    r"youtube\.com/@([a-zA-Z0-9_-]+)"          
]

# Kiểm tra URL kênh hợp lệ
def extract_channel_id(channel_url: str):
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, channel_url)
        if match:
            return match.group(1)
    return None

# Lấy danh sách video từ kênh YouTube
def get_channel_videos(channel_url: str):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' in info:
                return [entry['title'] for entry in info['entries'] if 'title' in entry]
        except Exception as e:
            print(f"Lỗi khi lấy danh sách video: {e}")
            return None
    return None

# Phân tích từ khóa từ danh sách video
def extract_keywords(video_titles):
    all_words = []
    
    for title in video_titles:
        words = re.findall(r'\b\w+\b', title.lower())  
        all_words.extend(words)
    
    word_counts = Counter(all_words)
    
    primary_keywords = [word for word, count in word_counts.items() if count >= 5]
    secondary_keywords = [word for word, count in word_counts.items() if 2 <= count < 5]
    extended_keywords = [word for word, count in word_counts.items() if count == 1]
    
    df = pd.DataFrame({
        "Từ khóa": primary_keywords + secondary_keywords + extended_keywords,
        "Loại": (["Từ khóa chính"] * len(primary_keywords)) +
                (["Từ khóa phụ"] * len(secondary_keywords)) +
                (["Từ khóa mở rộng"] * len(extended_keywords)),
        "Số lần xuất hiện": [word_counts[word] for word in primary_keywords + secondary_keywords + extended_keywords]
    })

    return df.to_dict(orient="records")  

# API phân tích từ khóa
@app.post("/analyze")
def analyze_channel(data: YouTubeChannel):
    channel_url = data.channel_url

    # Kiểm tra URL hợp lệ
    channel_id = extract_channel_id(channel_url)
    if not channel_id:
        raise HTTPException(status_code=400, detail="URL kênh YouTube không hợp lệ! Vui lòng nhập đúng link.")

    # Lấy danh sách video
    video_titles = get_channel_videos(channel_url)
    if not video_titles:
        raise HTTPException(status_code=404, detail="Không thể lấy danh sách video từ kênh này!")

    # Trích xuất từ khóa
    keyword_analysis = extract_keywords(video_titles)

    return {"Kết quả phân tích từ khóa": keyword_analysis}
