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
    with engine.begin() as conn:
        tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}

        if 'users' in tables:
            user_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
            if 'password_hashed' not in user_cols:
                conn.execute(text('ALTER TABLE users ADD COLUMN password_hashed BOOLEAN DEFAULT 0'))
            if 'ban_count' not in user_cols:
                conn.execute(text('ALTER TABLE users ADD COLUMN ban_count INTEGER DEFAULT 0'))
            if 'ban_until' not in user_cols:
                conn.execute(text('ALTER TABLE users ADD COLUMN ban_until DATETIME DEFAULT NULL'))

        if 'tasks' in tables:
            task_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(tasks)"))}
            if 'required_gender' not in task_cols:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN required_gender VARCHAR(10) DEFAULT NULL'))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    run_startup_migrations()

    with Session(engine) as db:
        existing_count = db.query(TaskCategory).count()
        if existing_count == 0:
            for name, description, order in DEFAULT_CATEGORIES:
                db.add(TaskCategory(name=name, description=description, sort_order=order))
            db.commit()
