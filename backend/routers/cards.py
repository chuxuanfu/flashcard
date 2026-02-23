"""
卡片管理路由 - 直接间隔版本
"""
from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from backend.database import get_db
from backend.schemas import Card, CardCreate, CardUpdate, CardBrief, BatchMoveCards, BatchDeleteCards
from backend.routers.auth import get_current_user
from backend.utils.media import save_image, save_audio, delete_media
from backend.config import EBBINGHAUS_INTERVALS

router = APIRouter(prefix="/cards", tags=["卡片管理"])


def generate_schedule_for_card(cursor, card_id: int, start_date: date, completed_stages: set = None):
    """为卡片生成复习计划（直接间隔，不是累计）"""
    if completed_stages is None:
        completed_stages = set()
    
    cursor.execute("DELETE FROM review_schedule WHERE card_id = ?", (card_id,))
    
    first_pending = None
    for stage in range(1, len(EBBINGHAUS_INTERVALS)):
        days = EBBINGHAUS_INTERVALS[stage]
        scheduled_date = start_date + timedelta(days=days)
        reviewed = 1 if stage in completed_stages else 0
        
        cursor.execute("""
            INSERT INTO review_schedule (card_id, stage, scheduled_date, reviewed)
            VALUES (?, ?, ?, ?)
        """, (card_id, stage, scheduled_date.strftime("%Y-%m-%d"), reviewed))
        
        if not reviewed and first_pending is None:
            first_pending = scheduled_date
    
    return first_pending


def get_card_with_tags(cursor, card_id: int) -> dict:
    cursor.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    card = cursor.fetchone()
    if not card:
        return None
    
    card_dict = dict(card)
    cursor.execute("""
        SELECT t.id, t.name, t.color FROM tags t
        JOIN card_tags ct ON t.id = ct.tag_id WHERE ct.card_id = ?
    """, (card_id,))
    card_dict["tags"] = [dict(row) for row in cursor.fetchall()]
    return card_dict


@router.get("", response_model=List[CardBrief])
async def get_cards(
    tag_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    is_weak: Optional[bool] = Query(None),
    user: bool = Depends(get_current_user)
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT DISTINCT c.* FROM cards c"
        conditions, params = [], []
        
        if tag_id:
            query += " JOIN card_tags ct ON c.id = ct.card_id"
            conditions.append("ct.tag_id = ?")
            params.append(tag_id)
        if search:
            conditions.append("(c.question LIKE ? OR c.answer LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if is_weak is not None:
            conditions.append("c.is_weak = ?")
            params.append(is_weak)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY c.created_at DESC"
        
        cursor.execute(query, params)
        cards = []
        for row in cursor.fetchall():
            card_dict = dict(row)
            cursor.execute("""
                SELECT t.id, t.name, t.color FROM tags t
                JOIN card_tags ct ON t.id = ct.tag_id WHERE ct.card_id = ?
            """, (card_dict["id"],))
            card_dict["tags"] = [dict(t) for t in cursor.fetchall()]
            cards.append(card_dict)
        return cards


@router.get("/{card_id}", response_model=Card)
async def get_card(card_id: int, user: bool = Depends(get_current_user)):
    with get_db() as conn:
        card = get_card_with_tags(conn.cursor(), card_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        return card


@router.post("", response_model=Card)
async def create_card(
    question: str = Form(...),
    answer: str = Form(...),
    tag_ids: str = Form(""),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    user: bool = Depends(get_current_user)
):
    image_path = await save_image(image) if image else None
    audio_path = await save_audio(audio) if audio else None
    today = date.today()
    
    with get_db() as conn:
        cursor = conn.cursor()
        first_review = today + timedelta(days=EBBINGHAUS_INTERVALS[1])
        
        cursor.execute("""
            INSERT INTO cards (question, answer, image_path, audio_path, created_at, next_review, current_stage)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (question, answer, image_path, audio_path, today.strftime("%Y-%m-%d %H:%M:%S"), first_review))
        
        card_id = cursor.lastrowid
        generate_schedule_for_card(cursor, card_id, today)
        
        if tag_ids:
            for tid in tag_ids.split(","):
                tid = tid.strip()
                if tid.isdigit():
                    cursor.execute("INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?)", (card_id, int(tid)))
        
        return get_card_with_tags(cursor, card_id)


@router.put("/{card_id}", response_model=Card)
async def update_card(card_id: int, card: CardUpdate, user: bool = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        existing = get_card_with_tags(cursor, card_id)
        if not existing:
            raise HTTPException(status_code=404, detail="卡片不存在")
        
        updates, values = [], []
        
        if card.question is not None:
            updates.append("question = ?")
            values.append(card.question)
        if card.answer is not None:
            updates.append("answer = ?")
            values.append(card.answer)
        if card.is_weak is not None:
            updates.append("is_weak = ?")
            values.append(card.is_weak)
        
        if card.created_at is not None:
            try:
                new_created = datetime.strptime(card.created_at, "%Y-%m-%d")
                updates.append("created_at = ?")
                values.append(new_created.strftime("%Y-%m-%d %H:%M:%S"))
                
                cursor.execute("SELECT stage FROM review_schedule WHERE card_id = ? AND reviewed = 1", (card_id,))
                completed_stages = set(row[0] for row in cursor.fetchall())
                
                first_pending = generate_schedule_for_card(cursor, card_id, new_created.date(), completed_stages)
                updates.append("next_review = ?")
                values.append(first_pending.strftime("%Y-%m-%d") if first_pending else None)
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式错误")
        
        if updates:
            values.append(card_id)
            cursor.execute(f"UPDATE cards SET {', '.join(updates)} WHERE id = ?", values)
        
        if card.tag_ids is not None:
            cursor.execute("DELETE FROM card_tags WHERE card_id = ?", (card_id,))
            for tid in card.tag_ids:
                cursor.execute("INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?)", (card_id, tid))
        
        return get_card_with_tags(cursor, card_id)


@router.delete("/{card_id}")
async def delete_card(card_id: int, user: bool = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT image_path, audio_path FROM cards WHERE id = ?", (card_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="卡片不存在")
        delete_media(row["image_path"])
        delete_media(row["audio_path"])
        cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        return {"message": "删除成功"}


@router.post("/batch/move")
async def batch_move_cards(data: BatchMoveCards, user: bool = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        for card_id in data.card_ids:
            cursor.execute("DELETE FROM card_tags WHERE card_id = ?", (card_id,))
            for tag_id in data.tag_ids:
                cursor.execute("INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?)", (card_id, tag_id))
        return {"message": f"已移动 {len(data.card_ids)} 张卡片"}


@router.post("/batch/delete")
async def batch_delete_cards(data: BatchDeleteCards, user: bool = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        for card_id in data.card_ids:
            cursor.execute("SELECT image_path, audio_path FROM cards WHERE id = ?", (card_id,))
            row = cursor.fetchone()
            if row:
                delete_media(row["image_path"])
                delete_media(row["audio_path"])
            cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        return {"message": f"已删除 {len(data.card_ids)} 张卡片"}


@router.put("/{card_id}/media")
async def update_card_media_delete(card_id: int, data: dict, user: bool = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT image_path, audio_path FROM cards WHERE id = ?", (card_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="卡片不存在")
        
        updates = []
        if "image_path" in data and data["image_path"] is None:
            if row["image_path"]: delete_media(row["image_path"])
            updates.append("image_path = NULL")
        if "audio_path" in data and data["audio_path"] is None:
            if row["audio_path"]: delete_media(row["audio_path"])
            updates.append("audio_path = NULL")
        
        if updates:
            cursor.execute(f"UPDATE cards SET {', '.join(updates)} WHERE id = ?", (card_id,))
        return {"message": "已更新"}


@router.post("/{card_id}/media")
async def update_card_media_upload(
    card_id: int,
    question: str = Form(...),
    answer: str = Form(...),
    tag_ids: str = Form(""),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    user: bool = Depends(get_current_user)
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT image_path, audio_path FROM cards WHERE id = ?", (card_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="卡片不存在")
        
        updates, values = [], []
        if image:
            if row["image_path"]: delete_media(row["image_path"])
            updates.append("image_path = ?")
            values.append(await save_image(image))
        if audio:
            if row["audio_path"]: delete_media(row["audio_path"])
            updates.append("audio_path = ?")
            values.append(await save_audio(audio))
        
        if updates:
            values.append(card_id)
            cursor.execute(f"UPDATE cards SET {', '.join(updates)} WHERE id = ?", values)
        return {"message": "媒体已更新"}
