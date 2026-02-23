"""
复习功能路由 - 基于 review_schedule 表的新逻辑
"""
from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from backend.database import get_db
from backend.schemas import Card, ReviewAction, TodayReviewStats
from backend.routers.auth import get_current_user
from backend.utils.scheduler import get_stage_description
from backend.config import EBBINGHAUS_INTERVALS

router = APIRouter(prefix="/review", tags=["复习"])


def generate_schedule_for_card(cursor, card_id: int, start_date: date):
    """为卡片生成完整的复习计划"""
    # 删除旧的计划
    cursor.execute("DELETE FROM review_schedule WHERE card_id = ?", (card_id,))
    
    # 生成新计划（从 stage 1 开始）
    
    for stage in range(1, len(EBBINGHAUS_INTERVALS)):
        days = EBBINGHAUS_INTERVALS[stage]
        scheduled_date = start_date + timedelta(days=days)
        cursor.execute("""
            INSERT INTO review_schedule (card_id, stage, scheduled_date, reviewed)
            VALUES (?, ?, ?, 0)
        """, (card_id, stage, scheduled_date.strftime("%Y-%m-%d")))


@router.get("/today", response_model=List[Card])
async def get_today_cards(
    tag_id: Optional[int] = Query(None, description="按标签筛选"),
    user: bool = Depends(get_current_user)
):
    """
    获取今天需要复习的卡片
    逻辑：scheduled_date <= today 且 reviewed = 0 的卡片
    """
    today = date.today()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        if tag_id:
            query = """
                SELECT DISTINCT c.*, rs.stage as pending_stage, rs.scheduled_date as pending_date
                FROM cards c
                JOIN review_schedule rs ON c.id = rs.card_id
                JOIN card_tags ct ON c.id = ct.card_id
                WHERE ct.tag_id = ? 
                    AND rs.scheduled_date <= ? 
                    AND rs.reviewed = 0
                    AND c.completed = 0
                ORDER BY rs.scheduled_date ASC, rs.stage ASC
            """
            cursor.execute(query, (tag_id, today))
        else:
            query = """
                SELECT DISTINCT c.*, rs.stage as pending_stage, rs.scheduled_date as pending_date
                FROM cards c
                JOIN review_schedule rs ON c.id = rs.card_id
                WHERE rs.scheduled_date <= ? 
                    AND rs.reviewed = 0
                    AND c.completed = 0
                ORDER BY rs.scheduled_date ASC, rs.stage ASC
            """
            cursor.execute(query, (today,))
        
        # 用字典去重，每张卡片只出现一次（取最早的待复习阶段）
        seen_cards = {}
        for row in cursor.fetchall():
            card_dict = dict(row)
            card_id = card_dict["id"]
            if card_id not in seen_cards:
                # 获取标签
                cursor.execute("""
                    SELECT t.id, t.name, t.color 
                    FROM tags t
                    JOIN card_tags ct ON t.id = ct.tag_id
                    WHERE ct.card_id = ?
                """, (card_id,))
                card_dict["tags"] = [dict(t) for t in cursor.fetchall()]
                seen_cards[card_id] = card_dict
        
        return list(seen_cards.values())


@router.get("/today/stats", response_model=TodayReviewStats)
async def get_today_stats(user: bool = Depends(get_current_user)):
    """获取今日复习统计"""
    today = date.today()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 今日及之前需要复习的总数（去重卡片）
        cursor.execute("""
            SELECT COUNT(DISTINCT card_id) FROM review_schedule
            WHERE scheduled_date <= ? AND reviewed = 0
        """, (today,))
        total = cursor.fetchone()[0]
        
        # 今日已复习的数量
        cursor.execute("""
            SELECT COUNT(DISTINCT card_id) FROM review_schedule
            WHERE DATE(reviewed_at) = ? AND reviewed = 1
        """, (today,))
        completed = cursor.fetchone()[0]
        
        return TodayReviewStats(
            total=total,
            completed=completed,
            remaining=max(0, total)
        )


@router.post("/submit")
async def submit_review(
    action: ReviewAction,
    user: bool = Depends(get_current_user)
):
    """
    提交复习结果
    - 掌握：标记当前待复习阶段为已复习
    - 未掌握：标记为弱项，不改变复习计划状态（明天继续出现）
    """
    with get_db() as conn:
        cursor = conn.cursor()
        today = date.today()
        
        # 获取卡片
        cursor.execute("SELECT * FROM cards WHERE id = ?", (action.card_id,))
        card = cursor.fetchone()
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        
        card = dict(card)
        
        # 获取当前待复习的最早阶段
        cursor.execute("""
            SELECT * FROM review_schedule 
            WHERE card_id = ? AND scheduled_date <= ? AND reviewed = 0
            ORDER BY stage ASC
            LIMIT 1
        """, (action.card_id, today))
        pending_schedule = cursor.fetchone()
        
        if not pending_schedule:
            raise HTTPException(status_code=400, detail="没有待复习的内容")
        
        pending_schedule = dict(pending_schedule)
        current_stage = pending_schedule["stage"]
        
        # 记录复习历史
        cursor.execute("""
            INSERT INTO review_history (card_id, stage, mastered)
            VALUES (?, ?, ?)
        """, (action.card_id, current_stage, action.mastered))
        
        if action.mastered:
            # 掌握了：标记该阶段为已复习
            cursor.execute("""
                UPDATE review_schedule 
                SET reviewed = 1, reviewed_at = ?
                WHERE card_id = ? AND stage = ?
            """, (datetime.now().isoformat(), action.card_id, current_stage))
            
            # 更新卡片的 current_stage
            new_stage = current_stage
            cursor.execute("""
                UPDATE cards SET current_stage = ? WHERE id = ?
            """, (new_stage, action.card_id))
            
            # 检查是否完成所有复习
            cursor.execute("""
                SELECT COUNT(*) FROM review_schedule 
                WHERE card_id = ? AND reviewed = 0
            """, (action.card_id,))
            remaining = cursor.fetchone()[0]
            completed = remaining == 0
            
            if completed:
                cursor.execute("UPDATE cards SET completed = 1 WHERE id = ?", (action.card_id,))
            
            # 获取下次复习日期
            cursor.execute("""
                SELECT scheduled_date FROM review_schedule 
                WHERE card_id = ? AND reviewed = 0
                ORDER BY stage ASC
                LIMIT 1
            """, (action.card_id,))
            next_row = cursor.fetchone()
            next_review = next_row["scheduled_date"] if next_row else None
            
            # 更新 cards 表的 next_review 字段
            cursor.execute("""
                UPDATE cards SET next_review = ? WHERE id = ?
            """, (next_review, action.card_id))
            
            return {
                "message": "太棒了！继续保持！",
                "new_stage": new_stage,
                "next_review": next_review,
                "completed": completed,
                "stage_description": get_stage_description(new_stage)
            }
        else:
            # 没掌握：标记为弱项，不改变 review_schedule
            cursor.execute("""
                UPDATE cards SET is_weak = 1 WHERE id = ?
            """, (action.card_id,))
            
            return {
                "message": "没关系，明天继续加油！",
                "new_stage": current_stage - 1,
                "next_review": str(pending_schedule["scheduled_date"]),
                "completed": False,
                "stage_description": get_stage_description(current_stage - 1)
            }


@router.get("/weak", response_model=List[Card])
async def get_weak_cards(user: bool = Depends(get_current_user)):
    """获取所有标记为弱项的卡片"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM cards WHERE is_weak = 1
            ORDER BY created_at DESC
        """)
        
        cards = []
        for row in cursor.fetchall():
            card_dict = dict(row)
            cursor.execute("""
                SELECT t.id, t.name, t.color 
                FROM tags t
                JOIN card_tags ct ON t.id = ct.tag_id
                WHERE ct.card_id = ?
            """, (card_dict["id"],))
            card_dict["tags"] = [dict(t) for t in cursor.fetchall()]
            cards.append(card_dict)
        
        return cards


@router.delete("/weak/{card_id}")
async def remove_weak_mark(card_id: int, user: bool = Depends(get_current_user)):
    """取消弱项标记"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE cards SET is_weak = 0 WHERE id = ?", (card_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="卡片不存在")
        return {"message": "已取消弱项标记"}


@router.get("/schedule/{card_id}")
async def get_card_schedule(card_id: int, user: bool = Depends(get_current_user)):
    """获取单张卡片的复习计划"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
        card = cursor.fetchone()
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在")
        
        card = dict(card)
        
        # 获取复习计划
        cursor.execute("""
            SELECT * FROM review_schedule 
            WHERE card_id = ? 
            ORDER BY stage ASC
        """, (card_id,))
        schedule = [dict(row) for row in cursor.fetchall()]
        
        # 获取复习历史
        cursor.execute("""
            SELECT * FROM review_history 
            WHERE card_id = ? 
            ORDER BY reviewed_at ASC
        """, (card_id,))
        history = [dict(row) for row in cursor.fetchall()]
        
        # 计算当前阶段描述
        cursor.execute("""
            SELECT stage FROM review_schedule 
            WHERE card_id = ? AND reviewed = 1
            ORDER BY stage DESC
            LIMIT 1
        """, (card_id,))
        last_reviewed = cursor.fetchone()
        current_stage = last_reviewed["stage"] if last_reviewed else 0
        
        return {
            "card": card,
            "current_stage": current_stage,
            "stage_description": get_stage_description(current_stage),
            "next_review": card["next_review"],
            "completed": card["completed"],
            "schedule": schedule,
            "history": history
        }


@router.put("/schedule/{card_id}/stage/{stage}")
async def update_stage_reviewed(
    card_id: int, 
    stage: int,
    reviewed: bool,
    user: bool = Depends(get_current_user)
):
    """手动修改某个阶段的复习状态"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE review_schedule 
            SET reviewed = ?, reviewed_at = ?
            WHERE card_id = ? AND stage = ?
        """, (reviewed, datetime.now().isoformat() if reviewed else None, card_id, stage))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="未找到该复习计划")
        
        # 更新 cards 表的 next_review 和 current_stage
        cursor.execute("""
            SELECT MIN(scheduled_date) FROM review_schedule 
            WHERE card_id = ? AND reviewed = 0
        """, (card_id,))
        next_row = cursor.fetchone()
        next_review = next_row[0] if next_row and next_row[0] else None
        
        cursor.execute("""
            SELECT MAX(stage) FROM review_schedule 
            WHERE card_id = ? AND reviewed = 1
        """, (card_id,))
        stage_row = cursor.fetchone()
        current_stage = stage_row[0] if stage_row and stage_row[0] else 0
        
        cursor.execute("""
            UPDATE cards SET next_review = ?, current_stage = ? WHERE id = ?
        """, (next_review, current_stage, card_id))
        
        return {"message": "已更新"}
