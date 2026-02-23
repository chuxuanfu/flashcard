"""
应用配置文件
首次运行时请修改 PASSWORD 和 SECRET_KEY
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = DATA_DIR / "media"
IMAGES_DIR = MEDIA_DIR / "images"
AUDIO_DIR = MEDIA_DIR / "audio"
EXPORTS_DIR = BASE_DIR / "exports"

# 数据库
DATABASE_PATH = DATA_DIR / "flashcards.db"
BACKUP_PATH = DATA_DIR / "backup.json"

# 确保目录存在
for dir_path in [DATA_DIR, MEDIA_DIR, IMAGES_DIR, AUDIO_DIR, EXPORTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ============ 安全配置 - 请修改！ ============
# 登录密码（请改成你自己的密码）
PASSWORD = "todo"

# JWT 密钥（请改成随机字符串，可以用: openssl rand -hex 32）
SECRET_KEY = "todo"

# Token 过期时间（天）
TOKEN_EXPIRE_DAYS = 30
# =============================================

# JWT 配置
ALGORITHM = "HS256"

# 艾宾浩斯复习间隔（天数）
# Stage 0: 首次学习（当天）
# Stage 1-7: 后续复习
EBBINGHAUS_INTERVALS = [0, 1, 3, 7, 14, 30, 90, 365]

# 允许的文件类型
ALLOWED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_AUDIO_TYPES = {".mp3", ".m4a", ".wav", ".ogg", ".webm"}
