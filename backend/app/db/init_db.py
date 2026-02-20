from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models import TaskCategory


DEFAULT_CATEGORIES = [
    ('跑腿代办', '校园跑腿/代办服务', 1),
    ('学习辅导', '课程答疑、作业讲解', 2),
    ('技术服务', '编程、设计、剪辑等', 3),
    ('活动协助', '活动执行、摄影、主持', 4),
]


def run_startup_migrations() -> None:
    # SQLite quick migration for old schema compatibility.
    with engine.begin() as conn:
        table_info = conn.execute(text("PRAGMA table_info(users)"))
        columns = {row[1] for row in table_info}
        has_users_table = 'users' in {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        if has_users_table:
            if 'password_hashed' not in columns:
                conn.execute(text('ALTER TABLE users ADD COLUMN password_hashed BOOLEAN DEFAULT 0'))
            if 'ban_count' not in columns:
                conn.execute(text('ALTER TABLE users ADD COLUMN ban_count INTEGER DEFAULT 0'))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    run_startup_migrations()

    with Session(engine) as db:
        existing_count = db.query(TaskCategory).count()
        if existing_count == 0:
            for name, description, order in DEFAULT_CATEGORIES:
                db.add(TaskCategory(name=name, description=description, sort_order=order))
            db.commit()
