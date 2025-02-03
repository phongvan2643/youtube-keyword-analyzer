from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Định nghĩa dữ liệu đầu vào
class KeywordInput(BaseModel):
    keyword: str

# API gốc
@app.get("/")
def home():
    return {"message": "Hello, Render!"}

# API phân tích từ khóa YouTube
@app.post("/analyze")
def analyze_keyword(data: KeywordInput):
    keyword = data.keyword
    return {"keyword": keyword, "status": "success"}
