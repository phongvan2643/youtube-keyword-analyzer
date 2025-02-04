from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import re
from collections import Counter
import pandas as pd

app = FastAPI()

# API kiểm tra xem service có hoạt động không
@app.get("/")
def home():
    return {"message": "YouTube Keyword Analyzer API is running!"}

# Định nghĩa dữ liệu đầu vào
class YouTubeChannel(BaseModel):
    channel_url: str

# Định nghĩa các dạng URL hợp lệ của YouTube
YOUTUBE_URL_PATTERNS = [
    r"youtube\.com/channel/([a-zA-Z0-9_-]+)",  # Dạng /channel/ID
    r"youtube\.com/c/([a-zA-Z0-9_-]+)",        # Dạng /c/TênKênh
    r"youtube\.com/@([a-zA-Z0-9_-]+)"          # Dạng @TênKênh
]

# Hàm kiểm tra URL có hợp lệ không
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
            print(f"Lỗi khi lấy danh sách video: {e}")
            return None
    return None

# Hàm phân tích từ khóa từ danh sách tiêu đề video
def extract_keywords(video_titles):
    all_words = []
    
    for title in video_titles:
        words = re.findall(r'\b\w+\b', title.lower())  # Chuyển thành chữ thường và tách từ
        all_words.extend(words)
    
    # Đếm số lần xuất hiện của từ
    word_counts = Counter(all_words)
    
    # Phân loại từ khóa
    primary_keywords = [word for word, count in word_counts.items() if count >= 5]  # Từ khóa chính (xuất hiện >= 5 lần)
    secondary_keywords = [word for word, count in word_counts.items() if 2 <= count < 5]  # Từ khóa phụ (2-4 lần)
    extended_keywords = [word for word, count in word_counts.items() if count == 1]  # Từ khóa mở rộng (chỉ xuất hiện 1 lần)
    
    # Tạo DataFrame để hiển thị đẹp hơn
    df = pd.DataFrame({
        "Từ khóa": primary_keywords + secondary_keywords + extended_keywords,
        "Loại": (["Từ khóa chính"] * len(primary_keywords)) +
                (["Từ khóa phụ"] * len(secondary_keywords)) +
                (["Từ khóa mở rộng"] * len(extended_keywords)),
        "Số lần xuất hiện": [word_counts[word] for word in primary_keywords + secondary_keywords + extended_keywords]
    })

    return df.to_dict(orient="records")  # Trả về dạng JSON

# Endpoint phân tích từ khóa từ kênh YouTube
@app.post("/analyze")
def analyze_channel(data: YouTubeChannel):
    channel_url = data.channel_url

    # Kiểm tra URL có hợp lệ không
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
