from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import re
from collections import Counter
import pandas as pd

app = FastAPI()

# Định nghĩa các dạng URL hợp lệ của YouTube
YOUTUBE_URL_PATTERNS = [
    r"youtube\.com/channel/([a-zA-Z0-9_-]+)",  # Dạng /channel/ID
    r"youtube\.com/c/([a-zA-Z0-9_-]+)",       # Dạng /c/TênKênh
    r"youtube\.com/@([a-zA-Z0-9_-]+)",        # Dạng @TênKênh
]

class YouTubeChannel(BaseModel):
    channel_url: str

# Kiểm tra tính hợp lệ của URL kênh YouTube
def validate_youtube_channel_url(channel_url):
    if not any(re.search(pattern, channel_url) for pattern in YOUTUBE_URL_PATTERNS):
        raise HTTPException(status_code=400, detail="URL không hợp lệ! Vui lòng nhập link kênh YouTube hợp lệ.")
    return channel_url

# Hàm lấy danh sách video từ kênh YouTube
def get_channel_videos(channel_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # Chỉ lấy danh sách video, không tải về
        'force_generic_extractor': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' in info:
                return [entry['title'] for entry in info['entries'] if 'title' in entry]
            else:
                return []
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy video từ kênh: {str(e)}")

# Phân tích tiêu đề để trích xuất từ khóa
def analyze_keywords(video_titles):
    words = []
    for title in video_titles:
        words.extend(re.findall(r'\b\w+\b', title.lower()))  # Tách từ khóa theo từ
    word_counts = Counter(words)
    
    primary_keywords = [word for word, count in word_counts.items() if count > 5]  # Từ khóa chính (lặp lại nhiều)
    secondary_keywords = [word for word, count in word_counts.items() if 2 < count <= 5]  # Từ khóa phụ
    extended_keywords = [word for word, count in word_counts.items() if count == 2]  # Từ khóa mở rộng

    return primary_keywords, secondary_keywords, extended_keywords

@app.post("/analyze")
def analyze_youtube_keywords(channel: YouTubeChannel):
    channel_url = validate_youtube_channel_url(channel.channel_url)
    video_titles = get_channel_videos(channel_url)

    if not video_titles:
        raise HTTPException(status_code=500, detail="Không tìm thấy video nào trên kênh này.")

    primary_keywords, secondary_keywords, extended_keywords = analyze_keywords(video_titles)

    # Hiển thị dưới dạng bảng
    df = pd.DataFrame({
        "Từ khóa chính": [", ".join(primary_keywords) if primary_keywords else "Không có"],
        "Từ khóa phụ": [", ".join(secondary_keywords) if secondary_keywords else "Không có"],
        "Từ khóa mở rộng": [", ".join(extended_keywords) if extended_keywords else "Không có"],
    })

    return df.to_dict(orient="records")
