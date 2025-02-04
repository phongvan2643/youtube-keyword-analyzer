from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import re
from collections import Counter

app = FastAPI()

# Định nghĩa các dạng URL hợp lệ của kênh YouTube
YOUTUBE_URL_PATTERNS = [
    r"youtube\.com/channel/([a-zA-Z0-9_-]+)",  # Dạng /channel/ID
    r"youtube\.com/c/([a-zA-Z0-9_-]+)",        # Dạng /c/TênKênh
    r"youtube\.com/@([a-zA-Z0-9_-]+)"          # Dạng @TênKênh
]

class YouTubeChannel(BaseModel):
    channel_url: str

# Hàm kiểm tra và lấy Channel ID từ URL kênh YouTube
def extract_channel_id(channel_url: str):
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, channel_url)
        if match:
            return match.group(1)
    return None

# Hàm lấy danh sách video từ kênh YouTube
def get_channel_videos(channel_url: str):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # Chỉ lấy danh sách video, không tải video
        'force_generic_extractor': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' in info:
                return [entry['title'] for entry in info['entries'] if 'title' in entry]
        except Exception as e:
            print(f"Lỗi khi lấy video từ kênh: {str(e)}")
            return []
    return []

# Hàm trích xuất từ khóa từ danh sách tiêu đề video
def extract_keywords(video_titles):
    all_words = []
    
    for title in video_titles:
        words = re.findall(r'\b\w+\b', title.lower())  # Chuyển về chữ thường và tách từ
        all_words.extend(words)

    word_counts = Counter(all_words)

    # Phân loại từ khóa theo tần suất xuất hiện
    sorted_keywords = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

    primary_keywords = [word for word, count in sorted_keywords if count >= 5]  # Xuất hiện nhiều nhất
    secondary_keywords = [word for word, count in sorted_keywords if 3 <= count < 5]  # Xuất hiện trung bình
    extended_keywords = [word for word, count in sorted_keywords if count < 3]  # Xuất hiện ít hơn

    return {
        "Từ khóa chính": primary_keywords,
        "Từ khóa phụ": secondary_keywords,
        "Từ khóa mở rộng": extended_keywords
    }

# API Test route
@app.get("/")
def home():
    return {"message": "YouTube Keyword Analyzer API is running!"}

# API Endpoint để phân tích từ khóa từ kênh YouTube
@app.post("/analyze")
def analyze_channel(data: YouTubeChannel):
    channel_url = data.channel_url

    # Kiểm tra URL có hợp lệ không
    channel_id = extract_channel_id(channel_url)
    if not channel_id:
        raise HTTPException(status_code=400, detail="URL kênh YouTube không hợp lệ!")

    # Lấy danh sách video
    video_titles = get_channel_videos(channel_url)
    if not video_titles:
        raise HTTPException(status_code=404, detail="Không thể lấy danh sách video từ kênh này!")

    # Trích xuất từ khóa
    keyword_analysis = extract_keywords(video_titles)

    return keyword_analysis
