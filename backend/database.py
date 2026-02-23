"""
数据库连接和初始化
使用 SQLite
"""
import sqlite3
from contextlib import contextmanager
from backend.config import DATABASE_PATH


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row  # 返回字典格式
    conn.execute("PRAGMA foreign_keys = ON")  # 启用外键
    return conn


@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """初始化数据库表"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 卡片表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                image_path TEXT,
                audio_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_weak BOOLEAN DEFAULT 0,
                current_stage INTEGER DEFAULT 0,
                next_review DATE,
                completed BOOLEAN DEFAULT 0
            )
        """)
        
        # 标签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#3B82F6'
            )
        """)
        
        # 卡片-标签关联表（多对多）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_tags (
                card_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (card_id, tag_id),
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)
        
        # 复习历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stage INTEGER NOT NULL,
                mastered BOOLEAN NOT NULL,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
            )
        """)
        
        # 复习计划表 - 记录每个阶段的预定日期和完成状态
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                stage INTEGER NOT NULL,
                scheduled_date DATE NOT NULL,
                reviewed BOOLEAN DEFAULT 0,
                reviewed_at TIMESTAMP,
                UNIQUE(card_id, stage),
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_next_review ON cards(next_review)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_is_weak ON cards(is_weak)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_review_history_card ON review_history(card_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedule_card ON review_schedule(card_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedule_date ON review_schedule(scheduled_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedule_reviewed ON review_schedule(reviewed)")
        
        conn.commit()
        print("数据库初始化完成")


if __name__ == "__main__":
    init_database()
