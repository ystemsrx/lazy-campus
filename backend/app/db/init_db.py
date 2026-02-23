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
            if 'last_active' not in user_cols:
                conn.execute(text('ALTER TABLE users ADD COLUMN last_active DATETIME DEFAULT NULL'))
            for col in ('ban_publish', 'ban_accept', 'ban_contact'):
                if col not in user_cols:
                    conn.execute(text(f'ALTER TABLE users ADD COLUMN {col} BOOLEAN DEFAULT 0'))

        if 'tasks' in tables:
            task_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(tasks)"))}
            if 'required_gender' not in task_cols:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN required_gender VARCHAR(10) DEFAULT NULL'))
            if 'icon' not in task_cols:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN icon VARCHAR(50) DEFAULT NULL'))
            if 'is_pinned' not in task_cols:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN is_pinned BOOLEAN DEFAULT 0'))
            if 'is_urgent' not in task_cols:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN is_urgent BOOLEAN DEFAULT 0'))
            if 'admin_note' not in task_cols:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN admin_note TEXT DEFAULT NULL'))
            if 'is_deleted' not in task_cols:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0'))
                conn.execute(text('CREATE INDEX IF NOT EXISTS ix_tasks_is_deleted ON tasks (is_deleted)'))
            if 'deleted_at' not in task_cols:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN deleted_at DATETIME DEFAULT NULL'))

        if 'reports' in tables:
            report_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(reports)"))}
            if 'images' not in report_cols:
                conn.execute(text('ALTER TABLE reports ADD COLUMN images TEXT DEFAULT NULL'))
            if 'ban_penalty' not in report_cols:
                conn.execute(text('ALTER TABLE reports ADD COLUMN ban_penalty TEXT DEFAULT NULL'))
            if 'is_admin_ban' not in report_cols:
                conn.execute(text('ALTER TABLE reports ADD COLUMN is_admin_ban BOOLEAN DEFAULT 0'))

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

        if 'chat_messages' not in tables:
            conn.execute(text('''
                CREATE TABLE chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL REFERENCES users(id),
                    receiver_id INTEGER NOT NULL REFERENCES users(id),
                    task_id INTEGER REFERENCES tasks(id),
                    content TEXT NOT NULL,
                    is_read BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_messages_sender ON chat_messages (sender_id)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_messages_receiver ON chat_messages (receiver_id)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_messages_task ON chat_messages (task_id)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_messages_is_read ON chat_messages (is_read)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_messages_created ON chat_messages (created_at)'))
        else:
            cm_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(chat_messages)"))}
            if 'blocked' not in cm_cols:
                conn.execute(text('ALTER TABLE chat_messages ADD COLUMN blocked BOOLEAN DEFAULT 0'))

        if 'chat_attachments' not in tables:
            conn.execute(text('''
                CREATE TABLE chat_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uploader_id INTEGER NOT NULL REFERENCES users(id),
                    peer_id INTEGER NOT NULL REFERENCES users(id),
                    task_id INTEGER REFERENCES tasks(id),
                    message_id INTEGER REFERENCES chat_messages(id),
                    file_name VARCHAR(255) NOT NULL,
                    file_url VARCHAR(1000) NOT NULL,
                    file_size INTEGER NOT NULL,
                    mime_type VARCHAR(100) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_att_uploader ON chat_attachments (uploader_id)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_att_peer ON chat_attachments (peer_id)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_chat_att_task ON chat_attachments (task_id)'))

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
