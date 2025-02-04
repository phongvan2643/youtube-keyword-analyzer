from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import re
from collections import Counter
import pandas as pd

app = FastAPI()

# Định nghĩa các định dạng URL hợp lệ của kênh YouTube
YOUTUBE_URL_PATTERNS = [
    r"youtube\.com/channel/([a-zA-Z0-9_-]+)",  # Dạng /channel/ID
    r"youtube\.com/c/([a-zA-Z0-9_-]+)",        # Dạng /c/TênKênh
    r"youtube\.com/@([a-zA-Z0-9_-]+)"          # Dạng @TênKênh
]

class YouTubeChannel(BaseModel):
    channel_url: str

# Hàm kiểm tra và chuẩn hóa link kênh YouTube
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

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=False)
            videos = info.get('entries', [])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy dữ liệu: {str(e)}")

    return [{"title": video['title'], "url": video['url']} for video in videos]

# Hàm trích xuất từ khóa từ tiêu đề video
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
    channel_url = validate_youtube_channel_url(data.channel_url)

    videos = get_channel_videos(channel_url)
    if not videos:
        raise HTTPException(status_code=400, detail="Không tìm thấy video nào trên kênh này.")

    primary_keywords, secondary_keywords, extended_keywords = extract_keywords([v["title"] for v in videos])

    # Chuyển kết quả thành bảng
    df_videos = pd.DataFrame(videos[:20])  # Hiển thị 20 video đầu tiên
    df_primary_keywords = pd.DataFrame(primary_keywords, columns=["Từ khóa chính", "Số lần xuất hiện"])
    df_secondary_keywords = pd.DataFrame(secondary_keywords, columns=["Từ khóa phụ", "Số lần xuất hiện"])
    df_extended_keywords = pd.DataFrame(extended_keywords, columns=["Từ khóa mở rộng", "Số lần xuất hiện"])

    # Xuất ra JSON có dạng bảng
    return {
        "channel": channel_url,
        "total_videos": len(videos),
        "top_videos": df_videos.to_dict(orient="records"),
        "primary_keywords": df_primary_keywords.to_dict(orient="records"),
        "secondary_keywords": df_secondary_keywords.to_dict(orient="records"),
        "extended_keywords": df_extended_keywords.to_dict(orient="records")
    }
