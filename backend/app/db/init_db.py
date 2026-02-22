from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models import TaskCategory


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

        if 'reports' in tables:
            report_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(reports)"))}
            if 'images' not in report_cols:
                conn.execute(text('ALTER TABLE reports ADD COLUMN images TEXT DEFAULT NULL'))

        if 'worker_profiles' in tables:
            worker_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(worker_profiles)"))}
            if 'phone' not in worker_cols:
                conn.execute(text('ALTER TABLE worker_profiles ADD COLUMN phone VARCHAR(32) DEFAULT NULL'))
            if 'wechat' not in worker_cols:
                conn.execute(text('ALTER TABLE worker_profiles ADD COLUMN wechat VARCHAR(64) DEFAULT NULL'))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    run_startup_migrations()
