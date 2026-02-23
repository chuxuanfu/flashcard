"""
标签管理路由
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from backend.schemas import Tag, TagCreate, TagUpdate, TagMerge
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/tags", tags=["标签管理"])


@router.get("", response_model=List[Tag])
async def get_all_tags(user: bool = Depends(get_current_user)):
    """获取所有标签"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.name, t.color, COUNT(ct.card_id) as card_count
            FROM tags t
            LEFT JOIN card_tags ct ON t.id = ct.tag_id
            GROUP BY t.id
            ORDER BY t.name
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


@router.post("", response_model=Tag)
async def create_tag(tag: TagCreate, user: bool = Depends(get_current_user)):
    """创建标签"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO tags (name, color) VALUES (?, ?)",
                (tag.name, tag.color)
            )
            tag_id = cursor.lastrowid
            return {
                "id": tag_id,
                "name": tag.name,
                "color": tag.color,
                "card_count": 0
            }
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                raise HTTPException(status_code=400, detail="标签名已存在")
            raise


@router.put("/{tag_id}", response_model=Tag)
async def update_tag(
    tag_id: int, 
    tag: TagUpdate, 
    user: bool = Depends(get_current_user)
):
    """更新标签"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查标签是否存在
        cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="标签不存在")
        
        # 构建更新语句
        updates = []
        values = []
        if tag.name is not None:
            updates.append("name = ?")
            values.append(tag.name)
        if tag.color is not None:
            updates.append("color = ?")
            values.append(tag.color)
        
        if updates:
            values.append(tag_id)
            try:
                cursor.execute(
                    f"UPDATE tags SET {', '.join(updates)} WHERE id = ?",
                    values
                )
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    raise HTTPException(status_code=400, detail="标签名已存在")
                raise
        
        # 返回更新后的标签
        cursor.execute("""
            SELECT t.id, t.name, t.color, COUNT(ct.card_id) as card_count
            FROM tags t
            LEFT JOIN card_tags ct ON t.id = ct.tag_id
            WHERE t.id = ?
            GROUP BY t.id
        """, (tag_id,))
        return dict(cursor.fetchone())


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int, user: bool = Depends(get_current_user)):
    """删除标签（不删除关联的卡片）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="标签不存在")
        return {"message": "删除成功"}


@router.post("/merge")
async def merge_tags(merge: TagMerge, user: bool = Depends(get_current_user)):
    """合并多个标签"""
    if len(merge.source_tag_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要选择两个标签进行合并")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 创建新标签
        try:
            cursor.execute(
                "INSERT INTO tags (name) VALUES (?)",
                (merge.new_name,)
            )
            new_tag_id = cursor.lastrowid
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                raise HTTPException(status_code=400, detail="标签名已存在")
            raise
        
        # 获取所有相关卡片ID
        placeholders = ",".join("?" * len(merge.source_tag_ids))
        cursor.execute(f"""
            SELECT DISTINCT card_id FROM card_tags 
            WHERE tag_id IN ({placeholders})
        """, merge.source_tag_ids)
        card_ids = [row[0] for row in cursor.fetchall()]
        
        # 将卡片关联到新标签
        for card_id in card_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?)",
                (card_id, new_tag_id)
            )
        
        # 删除旧标签
        cursor.execute(f"DELETE FROM tags WHERE id IN ({placeholders})", merge.source_tag_ids)
        
        return {
            "message": "合并成功",
            "new_tag_id": new_tag_id,
            "cards_affected": len(card_ids)
        }
