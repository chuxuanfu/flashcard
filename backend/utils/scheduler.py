"""
艾宾浩斯遗忘曲线复习调度器
"""
from datetime import date, timedelta
from backend.config import EBBINGHAUS_INTERVALS


def calculate_next_review(current_stage: int, base_date: date = None) -> date:
    """
    计算下次复习日期
    
    Args:
        current_stage: 当前阶段 (0-7)
        base_date: 基准日期，默认今天
    
    Returns:
        下次复习日期
    """
    if base_date is None:
        base_date = date.today()
    
    # 如果已经完成所有阶段
    if current_stage >= len(EBBINGHAUS_INTERVALS) - 1:
        return None
    
    # 获取下一阶段的间隔天数
    next_stage = current_stage + 1
    days_until_next = EBBINGHAUS_INTERVALS[next_stage]
    
    # 从首次学习日期计算（stage 0 的日期）
    # 但这里我们用当前日期 + 间隔
    return base_date + timedelta(days=days_until_next)


def calculate_schedule_from_start(start_date: date) -> list:
    """
    从首次学习日期计算完整的复习计划
    
    Args:
        start_date: 首次学习日期
    
    Returns:
        复习日期列表
    """
    schedule = []
    cumulative_days = 0
    
    for i, interval in enumerate(EBBINGHAUS_INTERVALS):
        cumulative_days += interval
        review_date = start_date + timedelta(days=cumulative_days)
        schedule.append({
            "stage": i,
            "date": review_date,
            "interval_days": interval
        })
    
    return schedule


def get_stage_description(stage: int) -> str:
    """获取阶段的描述文字"""
    descriptions = [
        "首次学习",
        "第1次复习 (+1天)",
        "第2次复习 (+3天)",
        "第3次复习 (+1周)",
        "第4次复习 (+2周)",
        "第5次复习 (+1个月)",
        "第6次复习 (+3个月)",
        "第7次复习 (+1年)",
        "完成全部复习！"
    ]
    if stage < len(descriptions):
        return descriptions[stage]
    return "已完成"


def is_due_today(next_review: date) -> bool:
    """检查是否今天需要复习（包括过期的）"""
    if next_review is None:
        return False
    return next_review <= date.today()
