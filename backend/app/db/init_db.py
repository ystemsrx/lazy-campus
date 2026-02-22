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
            if 'show_contact' not in worker_cols:
                conn.execute(text('ALTER TABLE worker_profiles ADD COLUMN show_contact BOOLEAN DEFAULT 1'))

        if 'task_messages' in tables:
            msg_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(task_messages)"))}
            if 'session_assignee_id' not in msg_cols:
                conn.execute(text('ALTER TABLE task_messages ADD COLUMN session_assignee_id INTEGER DEFAULT NULL'))
                conn.execute(text('CREATE INDEX IF NOT EXISTS ix_task_messages_session_assignee_id ON task_messages (session_assignee_id)'))

        if 'task_abandon_logs' not in tables:
            conn.execute(text('''
                CREATE TABLE task_abandon_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_id INTEGER NOT NULL,
                    abandoned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_task_abandon_logs_user_id ON task_abandon_logs (user_id)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_task_abandon_logs_task_id ON task_abandon_logs (task_id)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_task_abandon_logs_abandoned_at ON task_abandon_logs (abandoned_at)'))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    run_startup_migrations()
