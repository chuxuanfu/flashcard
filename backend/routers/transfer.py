"""
导入导出功能路由
"""
import csv
import json
import zipfile
import shutil
from io import StringIO, BytesIO
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from backend.database import get_db
from backend.config import MEDIA_DIR, EXPORTS_DIR, DATA_DIR
from backend.schemas import ImportResult
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/transfer", tags=["导入导出"])


@router.get("/export")
async def export_data(
    format: str = Query("csv", description="导出格式: csv 或 json"),
    user: bool = Depends(get_current_user)
):
    """导出数据为 ZIP 文件（包含 CSV/JSON 和媒体文件）"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 获取所有卡片
        cursor.execute("SELECT * FROM cards ORDER BY id")
        cards = [dict(row) for row in cursor.fetchall()]
        
        # 获取每张卡片的标签
        for card in cards:
            cursor.execute("""
                SELECT t.name FROM tags t
                JOIN card_tags ct ON t.id = ct.tag_id
                WHERE ct.card_id = ?
            """, (card["id"],))
            card["tags"] = ";".join([row[0] for row in cursor.fetchall()])
        
        # 获取所有标签
        cursor.execute("SELECT * FROM tags ORDER BY id")
        tags = [dict(row) for row in cursor.fetchall()]
        
        # 获取复习历史
        cursor.execute("SELECT * FROM review_history ORDER BY id")
        history = [dict(row) for row in cursor.fetchall()]
    
    # 创建 ZIP 文件
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        if format == "csv":
            # 导出 CSV
            csv_buffer = StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["id", "question", "answer", "tags", "image", "audio", 
                           "created_at", "current_stage", "next_review", "is_weak", "completed"])
            for card in cards:
                writer.writerow([
                    card["id"],
                    card["question"],
                    card["answer"],
                    card["tags"],
                    card["image_path"] or "",
                    card["audio_path"] or "",
                    card["created_at"],
                    card["current_stage"],
                    card["next_review"],
                    card["is_weak"],
                    card["completed"]
                ])
            zf.writestr("data.csv", csv_buffer.getvalue())
        else:
            # 导出 JSON
            export_data = {
                "export_time": datetime.now().isoformat(),
                "cards": cards,
                "tags": tags,
                "review_history": history
            }
            zf.writestr("data.json", json.dumps(export_data, ensure_ascii=False, indent=2, default=str))
        
        # 添加媒体文件
        for card in cards:
            if card["image_path"]:
                image_file = MEDIA_DIR / card["image_path"]
                if image_file.exists():
                    zf.write(image_file, f"media/{card['image_path']}")
            if card["audio_path"]:
                audio_file = MEDIA_DIR / card["audio_path"]
                if audio_file.exists():
                    zf.write(audio_file, f"media/{card['audio_path']}")
    
    zip_buffer.seek(0)
    
    filename = f"flashcards_export_{timestamp}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/import", response_model=ImportResult)
async def import_data(
    file: UploadFile = File(...),
    user: bool = Depends(get_current_user)
):
    """导入数据（支持 CSV、JSON 或 ZIP）"""
    filename = file.filename.lower()
    content = await file.read()
    
    errors = []
    cards_imported = 0
    tags_imported = 0
    
    try:
        if filename.endswith(".zip"):
            # ZIP 文件处理
            with zipfile.ZipFile(BytesIO(content)) as zf:
                namelist = zf.namelist()
                
                # 解压媒体文件
                for name in namelist:
                    if name.startswith("media/") and not name.endswith("/"):
                        # 提取到媒体目录
                        target_path = MEDIA_DIR / name.replace("media/", "")
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(name) as src:
                            with open(target_path, "wb") as dst:
                                dst.write(src.read())
                
                # 处理数据文件
                if "data.json" in namelist:
                    with zf.open("data.json") as f:
                        data = json.loads(f.read().decode("utf-8"))
                        cards_imported, tags_imported, errors = _import_json(data)
                elif "data.csv" in namelist:
                    with zf.open("data.csv") as f:
                        csv_content = f.read().decode("utf-8")
                        cards_imported, errors = _import_csv(csv_content)
                else:
                    raise HTTPException(status_code=400, detail="ZIP 中没有找到 data.json 或 data.csv")
        
        elif filename.endswith(".json"):
            data = json.loads(content.decode("utf-8"))
            cards_imported, tags_imported, errors = _import_json(data)
        
        elif filename.endswith(".csv"):
            csv_content = content.decode("utf-8")
            cards_imported, errors = _import_csv(csv_content)
        
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 .csv, .json 或 .zip")
        
        return ImportResult(
            success=True,
            cards_imported=cards_imported,
            tags_imported=tags_imported,
            errors=errors
        )
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON 格式错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


def _import_json(data: dict):
    """导入 JSON 数据"""
    errors = []
    cards_imported = 0
    tags_imported = 0
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 导入标签
        tag_id_map = {}  # 旧ID -> 新ID
        if "tags" in data:
            for tag in data["tags"]:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)",
                        (tag["name"], tag.get("color", "#3B82F6"))
                    )
                    if cursor.lastrowid:
                        tag_id_map[tag["id"]] = cursor.lastrowid
                        tags_imported += 1
                    else:
                        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag["name"],))
                        row = cursor.fetchone()
                        if row:
                            tag_id_map[tag["id"]] = row[0]
                except Exception as e:
                    errors.append(f"标签 '{tag.get('name')}' 导入失败: {str(e)}")
        
        # 导入卡片
        if "cards" in data:
            for card in data["cards"]:
                try:
                    cursor.execute("""
                        INSERT INTO cards (question, answer, image_path, audio_path, 
                            created_at, is_weak, current_stage, next_review, completed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        card["question"],
                        card["answer"],
                        card.get("image_path"),
                        card.get("audio_path"),
                        card.get("created_at"),
                        card.get("is_weak", 0),
                        card.get("current_stage", 0),
                        card.get("next_review"),
                        card.get("completed", 0)
                    ))
                    new_card_id = cursor.lastrowid
                    cards_imported += 1
                    
                    # 处理标签关联
                    if "tags" in card and isinstance(card["tags"], str):
                        for tag_name in card["tags"].split(";"):
                            tag_name = tag_name.strip()
                            if tag_name:
                                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                                row = cursor.fetchone()
                                if row:
                                    cursor.execute(
                                        "INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?)",
                                        (new_card_id, row[0])
                                    )
                except Exception as e:
                    errors.append(f"卡片导入失败: {str(e)}")
    
    return cards_imported, tags_imported, errors


def _import_csv(csv_content: str):
    """导入 CSV 数据"""
    errors = []
    cards_imported = 0
    
    reader = csv.DictReader(StringIO(csv_content))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for i, row in enumerate(reader, 1):
            try:
                # 处理标签
                tag_names = row.get("tags", "").split(";")
                tag_ids = []
                for tag_name in tag_names:
                    tag_name = tag_name.strip()
                    if tag_name:
                        cursor.execute(
                            "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                            (tag_name,)
                        )
                        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                        tag_row = cursor.fetchone()
                        if tag_row:
                            tag_ids.append(tag_row[0])
                
                # 插入卡片
                cursor.execute("""
                    INSERT INTO cards (question, answer, image_path, audio_path)
                    VALUES (?, ?, ?, ?)
                """, (
                    row["question"],
                    row["answer"],
                    row.get("image") or None,
                    row.get("audio") or None
                ))
                card_id = cursor.lastrowid
                
                # 关联标签
                for tag_id in tag_ids:
                    cursor.execute(
                        "INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?)",
                        (card_id, tag_id)
                    )
                
                cards_imported += 1
            except Exception as e:
                errors.append(f"第 {i} 行导入失败: {str(e)}")
    
    return cards_imported, errors


@router.get("/backup")
async def create_backup(user: bool = Depends(get_current_user)):
    """创建完整备份（JSON 格式）"""
    from backend.config import BACKUP_PATH
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cards ORDER BY id")
        cards = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM tags ORDER BY id")
        tags = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM card_tags")
        card_tags = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM review_history ORDER BY id")
        history = [dict(row) for row in cursor.fetchall()]
    
    backup_data = {
        "backup_time": datetime.now().isoformat(),
        "cards": cards,
        "tags": tags,
        "card_tags": card_tags,
        "review_history": history
    }
    
    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
    
    return {"message": "备份成功", "path": str(BACKUP_PATH)}


@router.get("/template")
async def download_template():
    """下载 CSV 导入模板"""
    csv_content = """question,answer,tags,image,audio
"什么是光合作用？","植物利用阳光将二氧化碳和水转化为葡萄糖和氧气的过程","生物;高中","",""
"Apple 怎么读？","苹果 [ˈæpl]","英语;单词","","audio/apple.mp3"
"1+1=?","2","数学","",""
"""
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=import_template.csv"}
    )
