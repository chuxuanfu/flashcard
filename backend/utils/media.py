"""
媒体文件处理工具
处理图片和音频的上传、保存、删除
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import UploadFile, HTTPException
from backend.config import (
    IMAGES_DIR, AUDIO_DIR, 
    ALLOWED_IMAGE_TYPES, ALLOWED_AUDIO_TYPES
)


def generate_filename(original_filename: str) -> str:
    """生成唯一文件名"""
    ext = Path(original_filename).suffix.lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{unique_id}{ext}"


async def save_image(file: UploadFile) -> str:
    """
    保存图片文件
    
    Returns:
        相对路径 (images/xxx.jpg)
    """
    if not file:
        return None
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的图片格式: {ext}。支持: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    filename = generate_filename(file.filename)
    filepath = IMAGES_DIR / filename
    
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    return f"images/{filename}"


async def save_audio(file: UploadFile) -> str:
    """
    保存音频文件
    
    Returns:
        相对路径 (audio/xxx.mp3)
    """
    if not file:
        return None
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的音频格式: {ext}。支持: {', '.join(ALLOWED_AUDIO_TYPES)}"
        )
    
    filename = generate_filename(file.filename)
    filepath = AUDIO_DIR / filename
    
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    return f"audio/{filename}"


def delete_media(relative_path: str) -> bool:
    """删除媒体文件"""
    if not relative_path:
        return True
    
    from backend.config import MEDIA_DIR
    filepath = MEDIA_DIR / relative_path
    
    if filepath.exists():
        os.remove(filepath)
        return True
    return False


def get_media_full_path(relative_path: str) -> Path:
    """获取媒体文件的完整路径"""
    if not relative_path:
        return None
    from backend.config import MEDIA_DIR
    return MEDIA_DIR / relative_path
