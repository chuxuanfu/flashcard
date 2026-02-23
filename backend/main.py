"""
FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pathlib import Path

from backend.database import init_database
from backend.config import MEDIA_DIR, BASE_DIR
from backend.routers import auth, cards, tags, review, transfer

# 初始化数据库
init_database()

# 创建应用
app = FastAPI(
    title="Flashcard 复习系统",
    description="基于艾宾浩斯遗忘曲线的个人复习系统",
    version="1.0.0"
)

# CORS 配置（允许所有来源，因为是个人使用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(transfer.router, prefix="/api")

# 静态文件服务
frontend_path = BASE_DIR / "frontend"
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# 前端页面路由
@app.get("/")
async def root():
    return FileResponse(frontend_path / "index.html")


@app.get("/favicon.ico")
async def favicon():
    # 返回一个简单的 emoji favicon
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">📚</text></svg>'''
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
async def apple_touch_icon():
    # 返回空响应避免 404
    return Response(status_code=204)


# 健康检查
@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "Flashcard 系统运行正常"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
