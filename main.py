from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import re
from collections import Counter
import pandas as pd

app = FastAPI()

# Định nghĩa các dạng URL hợp lệ của kênh YouTube
YOUTUBE_URL_PATTERNS = [
    r"youtube\.com/channel/([a-zA-Z0-9_-]+)",  # Dạng /channel/ID
    r"youtube\.com/c/([a-zA-Z0-9_-]+)",       # Dạng /c/TênKênh
    r"youtube\.com/@([a-zA-Z0-9_-]+)"         # Dạng @TênKênh
]

class YouTubeChannel(BaseModel):
    channel_url: str

# Hàm kiểm tra URL có hợp lệ không
def validate_youtube_channel_url(channel_url):
    if not any(re.search(pattern, channel_url) for pattern in YOUTUBE_URL_PATTERNS):
        raise HTTPException(status_code=400, detail="URL không hợp lệ! Vui lòng nhập đúng link kênh YouTube.")
    return channel_url

# Hàm lấy danh sách video từ kênh YouTube
def get_channel_videos(channel_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # Chỉ lấy danh sách video, không tải
        'force_generic_extractor': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' not in info:
                raise HTTPException(status_code=404, detail="Không tìm thấy video nào trong kênh này.")
            return [video['title'] for video in info['entries'] if 'title' in video]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy dữ liệu từ YouTube: {str(e)}")

# Hàm trích xuất từ khóa từ danh sách tiêu đề video
def extract_keywords(video_titles):
    all_keywords = []
    for title in video_titles:
        words = re.findall(r'\b\w+\b', title.lower())  # Tách từ khóa
        all_keywords.extend(words)

    keyword_counts = Counter(all_keywords)
    sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)

    # Phân loại từ khóa
    primary_keywords = [kw for kw, count in sorted_keywords if count >= 3]  # Xuất hiện ít nhất 3 lần
    secondary_keywords = [kw for kw, count in sorted_keywords if 2 <= count < 3]
    extended_keywords = [kw for kw, count in sorted_keywords if count == 1]

    return primary_keywords, secondary_keywords, extended_keywords

@app.post("/analyze")
def analyze_channel(data: YouTubeChannel):
    channel_url = validate_youtube_channel_url(data.channel_url)
    video_titles = get_channel_videos(channel_url)

    primary_keywords, secondary_keywords, extended_keywords = extract_keywords(video_titles)

    # Chuyển kết quả thành bảng Pandas
    df = pd.DataFrame({
        "Từ khóa chính": primary_keywords[:20],
        "Từ khóa phụ": secondary_keywords[:20],
        "Từ khóa mở rộng": extended_keywords[:20],
    })

    return df.to_dict(orient="records")
