import io
import json
import logging
import os
import re
import shlex
import shutil
import signal
import subprocess
import threading
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.config import settings
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.agent import AgentMessage, AgentSession
from app.models.task import Task

try:
    from redis import Redis
except Exception:  # pragma: no cover - optional dependency at runtime
    Redis = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

MAX_AGENT_FILES_PER_MESSAGE = 5
MAX_AGENT_FILE_SIZE = 50 * 1024 * 1024
MAX_AGENT_INTERACTIONS = 8
AGENT_IDLE_TTL_MINUTES = 5
AGENT_QUEUE_GRACE_SECONDS = 5 * 60
AGENT_ERROR_PREFIX = '__AGENT_ERROR__:'
PROCESS_ENCODING = 'utf-8'

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_ROOT = PROJECT_ROOT / 'backend' / 'agent'
AGENT_TEMPLATE_WORKSPACE = AGENT_ROOT / 'workspace'
AGENT_CONFIG_FILE = AGENT_ROOT / 'config.sh'
AGENT_ENV_FILE = AGENT_ROOT / '.env'
AGENT_SKILLS_DIR = AGENT_ROOT / 'skills'
AGENT_SESSIONS_ROOT = PROJECT_ROOT / 'backend' / 'agent_sessions'

AGENT_RUN_LOCK = threading.Lock()
_CLEANER_LOCK = threading.Lock()
_CLEANER_STARTED = False
_RUNTIME_LOCK = threading.Lock()
_RUNNING_EXEC: dict[str, subprocess.Popen] = {}
_RUNNING_CONTAINER: dict[str, str] = {}
_CANCEL_REQUESTED_SESSIONS: set[str] = set()
_TERMINAL_TASK_STATUSES = {'completed', 'canceled'}
_QUEUE_LOCK = threading.Lock()
_QUEUE_COND = threading.Condition(_QUEUE_LOCK)
_QUEUE_WORKER_STARTED = False
_QUEUE_ITEMS: list['QueuedAgentRun'] = []
_QUEUED_SESSION_IDS: set[str] = set()
_RUNNING_SESSION_ID: str | None = None
_ACTIVE_OWNER_USER_ID: int | None = None
_OWNER_GRACE_UNTIL: datetime | None = None
_REDIS_CLIENT: Redis | None = None
_REDIS_CLIENT_LOCK = threading.Lock()
_REDIS_RETRY_UNTIL_TS = 0.0
_REDIS_DISABLED_LOGGED = False

AGENT_QUEUE_REDIS_RETRY_SECONDS = 5
AGENT_QUEUE_REDIS_POLL_SECONDS = 1.0
AGENT_QUEUE_RUNNING_TTL_SECONDS = 120
AGENT_QUEUE_RUNNING_HEARTBEAT_SECONDS = 20

_QUEUE_KEY_PREFIX = (settings.agent_queue_key_prefix or 'campus_task:agent_queue').strip() or 'campus_task:agent_queue'
_REDIS_QUEUE_LIST_KEY = f'{_QUEUE_KEY_PREFIX}:pending'
_REDIS_QUEUE_PAYLOADS_KEY = f'{_QUEUE_KEY_PREFIX}:payloads'
_REDIS_QUEUE_RUNNING_KEY = f'{_QUEUE_KEY_PREFIX}:running'

_REDIS_ENQUEUE_SCRIPT = """
if redis.call('HSETNX', KEYS[1], ARGV[1], ARGV[2]) == 1 then
  redis.call('RPUSH', KEYS[2], ARGV[1])
  return 1
end
return 0
"""

_REDIS_DEQUEUE_SCRIPT = """
local removed = redis.call('HDEL', KEYS[1], ARGV[1])
if removed == 0 then
  return 0
end
redis.call('LREM', KEYS[2], 0, ARGV[1])
return 1
"""

_REDIS_POP_NEXT_SCRIPT = """
if redis.call('GET', KEYS[3]) then
  return {'__BUSY__'}
end
while true do
  local session_id = redis.call('LPOP', KEYS[2])
  if not session_id then
    return {'__EMPTY__'}
  end
  local payload = redis.call('HGET', KEYS[1], session_id)
  redis.call('HDEL', KEYS[1], session_id)
  if payload then
    redis.call('SET', KEYS[3], session_id, 'EX', ARGV[1])
    return {session_id, payload}
  end
end
"""

_REDIS_TOUCH_RUNNING_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
  return 1
end
return 0
"""

_REDIS_CLEAR_RUNNING_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  redis.call('DEL', KEYS[1])
  return 1
end
return 0
"""


@dataclass
class QueuedAgentRun:
    session_id: str
    user_id: int
    user_prompt: str
    attachments: list[dict[str, Any]]
    queued_at: datetime


def utcnow() -> datetime:
    return datetime.utcnow()


def is_agent_busy() -> bool:
    return AGENT_RUN_LOCK.locked()


def session_root_dir(user_id: int, session_id: str) -> Path:
    return AGENT_SESSIONS_ROOT / str(user_id) / session_id


def workspace_dir(user_id: int, session_id: str) -> Path:
    return session_root_dir(user_id, session_id) / 'workspace'


def kimi_home_dir(user_id: int, session_id: str) -> Path:
    return session_root_dir(user_id, session_id) / 'kimi_home'


def uploads_dir(user_id: int, session_id: str) -> Path:
    return workspace_dir(user_id, session_id) / 'uploads'


def deliverables_dir(user_id: int, session_id: str) -> Path:
    return workspace_dir(user_id, session_id) / 'deliverables'


def ensure_agent_roots() -> None:
    AGENT_SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)


def _chmod_if_possible(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except Exception:
        # On some filesystems (e.g. Windows mounts), chmod may be ignored or denied.
        pass


def ensure_session_workspace(user_id: int, session_id: str) -> None:
    ensure_agent_roots()
    root_dir = session_root_dir(user_id, session_id)
    ws_dir = workspace_dir(user_id, session_id)
    kimi_dir = kimi_home_dir(user_id, session_id)
    root_dir.mkdir(parents=True, exist_ok=True)
    kimi_dir.mkdir(parents=True, exist_ok=True)

    if not ws_dir.exists():
        if AGENT_TEMPLATE_WORKSPACE.exists():
            shutil.copytree(AGENT_TEMPLATE_WORKSPACE, ws_dir)
        else:
            ws_dir.mkdir(parents=True, exist_ok=True)

    deliverables = deliverables_dir(user_id, session_id)
    uploads = uploads_dir(user_id, session_id)
    deliverables.mkdir(parents=True, exist_ok=True)
    uploads.mkdir(parents=True, exist_ok=True)

    # Ensure container process can write to mounted runtime directories.
    _chmod_if_possible(root_dir, 0o777)
    _chmod_if_possible(ws_dir, 0o777)
    _chmod_if_possible(kimi_dir, 0o777)
    _chmod_if_possible(deliverables, 0o777)
    _chmod_if_possible(uploads, 0o777)


def cleanup_workspace_keep_deliverables(user_id: int, session_id: str) -> None:
    ws_dir = workspace_dir(user_id, session_id)
    if not ws_dir.exists():
        return

    keep_dir = deliverables_dir(user_id, session_id)
    keep_dir.mkdir(parents=True, exist_ok=True)

    for item in ws_dir.iterdir():
        if item == keep_dir:
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)


def safe_filename(name: str) -> str:
    base = Path(name).name
    return re.sub(r'[^A-Za-z0-9._-]+', '_', base).strip('._') or 'file'


def normalize_uploaded_filename(name: str | None) -> str:
    base = Path(name or '').name.strip()
    return base or 'unnamed'


def resolve_unique_upload_name(target_dir: Path, name: str | None, seen: set[str] | None = None) -> str:
    candidate = normalize_uploaded_filename(name)
    stem = Path(candidate).stem or 'unnamed'
    suffix = Path(candidate).suffix

    taken = seen if seen is not None else set()
    index = 1
    while candidate in taken or (target_dir / candidate).exists():
        candidate = f'{stem}({index}){suffix}'
        index += 1

    if seen is not None:
        seen.add(candidate)
    return candidate


def sanitize_cli_risky_prompt(prompt: str) -> str:
    text = prompt.strip()
    if text.startswith('/') and len(text) < 10:
        return text[1:].lstrip()
    return text


def create_agent_message(
    db: Session,
    *,
    session_id: str,
    role: str,
    content: str | None = None,
    tool_name: str | None = None,
    tool_arguments: str | None = None,
    tool_call_id: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> AgentMessage:
    msg = AgentMessage(
        session_id=session_id,
        role=role,
        content=content,
        tool_name=tool_name,
        tool_arguments=tool_arguments,
        tool_call_id=tool_call_id,
        attachments_json=json.dumps(attachments, ensure_ascii=False) if attachments else None,
    )
    db.add(msg)
    db.flush()
    return msg


def _run_command(cmd: list[str], timeout: int = 120) -> str:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding=PROCESS_ENCODING,
        errors='replace',
        timeout=timeout,
    )
    if result.returncode != 0:
        stderr = (result.stderr or '').strip()
        stdout = (result.stdout or '').strip()
        detail = stderr or stdout or f'command failed: {" ".join(cmd)}'
        raise RuntimeError(detail)
    return (result.stdout or '').strip()


def _container_is_running(container_id: str) -> bool:
    try:
        out = _run_command(['docker', 'inspect', '-f', '{{.State.Running}}', container_id], timeout=20)
    except Exception:
        return False
    return out.strip().lower() == 'true'


def _stop_container(container_id: str | None) -> None:
    if not container_id:
        return
    try:
        subprocess.run(
            ['docker', 'rm', '-f', container_id],
            capture_output=True,
            text=True,
            encoding=PROCESS_ENCODING,
            errors='replace',
            timeout=30,
        )
    except Exception:
        logger.warning('failed to stop container %s', container_id, exc_info=True)


def _start_container(user_id: int, session_id: str) -> str:
    ensure_session_workspace(user_id, session_id)

    if not AGENT_CONFIG_FILE.exists():
        raise RuntimeError(f'缺少代理配置文件: {AGENT_CONFIG_FILE}')
    if not AGENT_ENV_FILE.exists():
        raise RuntimeError(f'缺少代理环境文件: {AGENT_ENV_FILE}')
    if not AGENT_SKILLS_DIR.exists():
        raise RuntimeError(f'缺少代理技能目录: {AGENT_SKILLS_DIR}')

    cmd = [
        'docker',
        'run',
        '--rm',
        '-d',
        '--hostname',
        'agent',
        '--env-file',
        str(AGENT_ENV_FILE),
        '--cpus=1.0',
        '--memory=512m',
        '--memory-swap=1g',
        '--pids-limit=128',
        '--ulimit',
        'nofile=1024:1024',
        '--cap-drop=ALL',
        '-v',
        f'{AGENT_CONFIG_FILE}:/config.sh:ro',
        '-v',
        f'{AGENT_SKILLS_DIR}:/root/.config/agents/skills:ro',
        '-v',
        f'{workspace_dir(user_id, session_id)}:/workspace',
        '-v',
        f'{kimi_home_dir(user_id, session_id)}:/root/.kimi',
        '-w',
        '/workspace',
        'agent-sandbox:cn',
        'bash',
        '-lc',
        "source /config.sh; trap 'exit 0' TERM INT; while true; do sleep 3600; done",
    ]
    out = _run_command(cmd, timeout=120)
    container_id = out.splitlines()[-1].strip()
    if not container_id:
        raise RuntimeError('启动容器失败，未返回容器 ID')
    return container_id


def _build_prompt(user_prompt: str, attachments: list[dict[str, Any]]) -> str:
    prompt = sanitize_cli_risky_prompt(user_prompt)
    if not attachments:
        return prompt

    lines = ['', '<hint>']
    lines.append('The user uploaded files in this message. You can read them directly under /workspace/uploads:')
    for att in attachments:
        path = att.get('workspace_path') or att.get('stored_name') or att.get('name')
        original = att.get('name') or ''
        lines.append(f'- {path} (original name: {original})')
    lines.append('</hint>')
    return f'{prompt}\n' + '\n'.join(lines)


def _persist_stream_line(db: Session, session_id: str, line: str) -> None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        text = line.strip()
        if text.startswith(AGENT_ERROR_PREFIX):
            text = text[len(AGENT_ERROR_PREFIX):].strip()
        create_agent_message(db, session_id=session_id, role='system', content=text)
        db.commit()
        return

    role = str(payload.get('role') or '').strip().lower() or 'assistant'
    if role == 'assistant':
        content = payload.get('content')
        if isinstance(content, str) and content.strip():
            create_agent_message(db, session_id=session_id, role='assistant', content=content)

        tool_calls = payload.get('tool_calls')
        if isinstance(tool_calls, list):
            for call in tool_calls:
                if not isinstance(call, dict):
                    continue
                function = call.get('function') if isinstance(call.get('function'), dict) else {}
                tool_name = function.get('name') if isinstance(function, dict) else None
                tool_args = function.get('arguments') if isinstance(function, dict) else None
                call_id = call.get('id')
                create_agent_message(
                    db,
                    session_id=session_id,
                    role='tool_call',
                    tool_name=str(tool_name) if tool_name is not None else None,
                    tool_arguments=str(tool_args) if tool_args is not None else None,
                    tool_call_id=str(call_id) if call_id is not None else None,
                )
        db.commit()
        return

    if role == 'tool':
        create_agent_message(
            db,
            session_id=session_id,
            role='tool',
            content=str(payload.get('content') or ''),
            tool_call_id=str(payload.get('tool_call_id') or '') or None,
        )
        db.commit()
        return

    create_agent_message(db, session_id=session_id, role='system', content=json.dumps(payload, ensure_ascii=False))
    db.commit()


def _prepare_container_for_session(db: Session, session: AgentSession) -> None:
    others = (
        db.query(AgentSession)
        .filter(AgentSession.id != session.id, AgentSession.container_id.isnot(None))
        .all()
    )
    for other in others:
        _stop_container(other.container_id)
        cleanup_workspace_keep_deliverables(other.user_id, other.id)
        other.container_id = None
        if other.status != 'queued':
            other.status = 'idle'
        other.last_error = None
        db.add(other)

    if session.container_id and not _container_is_running(session.container_id):
        session.container_id = None

    if not session.container_id:
        session.container_id = _start_container(session.user_id, session.id)

    db.add(session)
    db.commit()


def _append_system_error(session_id: str, error_text: str) -> None:
    with SessionLocal() as db:
        session = db.get(AgentSession, session_id)
        if session:
            session.status = 'error'
            session.last_error = error_text
            session.last_activity_at = utcnow()
            db.add(session)
        create_agent_message(db, session_id=session_id, role='system', content=error_text)
        db.commit()


def _register_running_exec(session_id: str, container_id: str, process: subprocess.Popen) -> None:
    with _RUNTIME_LOCK:
        _RUNNING_EXEC[session_id] = process
        _RUNNING_CONTAINER[session_id] = container_id


def _unregister_running_exec(session_id: str) -> None:
    with _RUNTIME_LOCK:
        _RUNNING_EXEC.pop(session_id, None)
        _RUNNING_CONTAINER.pop(session_id, None)


def _take_cancel_requested(session_id: str) -> bool:
    with _RUNTIME_LOCK:
        if session_id not in _CANCEL_REQUESTED_SESSIONS:
            return False
        _CANCEL_REQUESTED_SESSIONS.discard(session_id)
        return True


def _is_cancel_requested(session_id: str) -> bool:
    with _RUNTIME_LOCK:
        return session_id in _CANCEL_REQUESTED_SESSIONS


def _try_interrupt_container_process(container_id: str | None) -> bool:
    if not container_id:
        return False
    try:
        subprocess.run(
            [
                'docker',
                'exec',
                container_id,
                'bash',
                '-lc',
                'pkill -INT -f "kimi|kimi-code" >/dev/null 2>&1 || true',
            ],
            capture_output=True,
            text=True,
            encoding=PROCESS_ENCODING,
            errors='replace',
            timeout=20,
        )
        return True
    except Exception:
        logger.warning('failed to send INT into container %s', container_id, exc_info=True)
        return False


def interrupt_agent_session(db: Session, session: AgentSession) -> bool:
    process: subprocess.Popen | None = None
    container_id = session.container_id
    with _RUNTIME_LOCK:
        _CANCEL_REQUESTED_SESSIONS.add(session.id)
        process = _RUNNING_EXEC.get(session.id)
        container_id = _RUNNING_CONTAINER.get(session.id) or container_id

    requested = True
    if process:
        try:
            if process.stdin and not process.stdin.closed:
                process.stdin.write('\x03')
                process.stdin.flush()
                requested = True
        except Exception:
            logger.warning('failed to write Ctrl+C to session=%s', session.id, exc_info=True)

        try:
            interrupt_signal = signal.SIGINT
            if os.name == 'nt' and hasattr(signal, 'CTRL_BREAK_EVENT'):
                interrupt_signal = signal.CTRL_BREAK_EVENT
            process.send_signal(interrupt_signal)
            requested = True
        except ValueError:
            logger.info(
                'interrupt signal not supported for session=%s on platform=%s; fallback to terminate/kill',
                session.id,
                os.name,
            )
        except Exception:
            logger.warning('failed to send interrupt signal to session=%s', session.id, exc_info=True)

    if _try_interrupt_container_process(container_id):
        requested = True

    # Escalate to force-stop to guarantee cancellation.
    if process and process.poll() is None:
        try:
            process.wait(timeout=2)
        except Exception:
            pass
    if process and process.poll() is None:
        try:
            process.terminate()
            requested = True
            process.wait(timeout=2)
        except Exception:
            logger.warning('failed to terminate process for session=%s', session.id, exc_info=True)
    if process and process.poll() is None:
        try:
            process.kill()
            requested = True
        except Exception:
            logger.warning('failed to kill process for session=%s', session.id, exc_info=True)

    if container_id:
        _stop_container(container_id)
        requested = True
        session.container_id = None

    if requested:
        session.last_activity_at = utcnow()
        session.last_error = None
        db.add(session)
    return requested


def release_task_agent_resources(db: Session, task_id: int) -> int:
    sessions = db.query(AgentSession).filter(AgentSession.task_id == task_id).all()
    if not sessions:
        return 0

    released = 0
    for session in sessions:
        if session.status == 'running' or session.container_id:
            interrupt_agent_session(db, session)
        if session.container_id:
            _stop_container(session.container_id)
            cleanup_workspace_keep_deliverables(session.user_id, session.id)
            released += 1
        session.container_id = None
        if session.status == 'running':
            session.status = 'idle'
        session.last_error = None
        session.last_activity_at = utcnow()
        db.add(session)
    return released


def release_session_container_now(db: Session, session: AgentSession) -> bool:
    if not session.container_id:
        return False
    _stop_container(session.container_id)
    cleanup_workspace_keep_deliverables(session.user_id, session.id)
    session.container_id = None
    if session.status == 'running':
        session.status = 'idle'
    session.last_error = None
    session.last_activity_at = utcnow()
    db.add(session)
    return True


def _task_is_terminal(task: Task | None) -> bool:
    if not task:
        return False
    status = getattr(task.status, 'value', task.status)
    return str(status) in _TERMINAL_TASK_STATUSES


def _cleanup_user_idle_containers(user_id: int) -> int:
    cleaned = 0
    with SessionLocal() as db:
        sessions = (
            db.query(AgentSession)
            .filter(
                AgentSession.user_id == user_id,
                AgentSession.container_id.isnot(None),
                AgentSession.status != 'running',
            )
            .all()
        )
        for session in sessions:
            _stop_container(session.container_id)
            cleanup_workspace_keep_deliverables(session.user_id, session.id)
            session.container_id = None
            session.last_error = None
            session.last_activity_at = utcnow()
            db.add(session)
            cleaned += 1
        if cleaned:
            db.commit()
    return cleaned


def _count_queue_ahead_users_locked(stop_at_session_id: str | None = None) -> int:
    ahead = 0
    if _RUNNING_SESSION_ID is not None:
        ahead += 1

    for item in _QUEUE_ITEMS:
        if stop_at_session_id and item.session_id == stop_at_session_id:
            break
        ahead += 1
    return ahead


def _is_redis_queue_configured() -> bool:
    return bool((settings.redis_url or '').strip()) and Redis is not None


def _mark_redis_client_unavailable(exc: Exception | None = None) -> None:
    global _REDIS_CLIENT, _REDIS_RETRY_UNTIL_TS
    _REDIS_CLIENT = None
    _REDIS_RETRY_UNTIL_TS = time.time() + AGENT_QUEUE_REDIS_RETRY_SECONDS
    if exc:
        logger.warning('agent queue redis unavailable: %s', exc)


def _get_redis_client() -> Redis | None:
    global _REDIS_CLIENT, _REDIS_DISABLED_LOGGED
    if not _is_redis_queue_configured():
        if not _REDIS_DISABLED_LOGGED:
            if not (settings.redis_url or '').strip():
                logger.info('agent queue redis disabled: REDIS_URL is empty')
            elif Redis is None:
                logger.warning('agent queue redis disabled: redis package is not installed')
            _REDIS_DISABLED_LOGGED = True
        return None

    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT
    if time.time() < _REDIS_RETRY_UNTIL_TS:
        return None

    with _REDIS_CLIENT_LOCK:
        if _REDIS_CLIENT is not None:
            return _REDIS_CLIENT
        if time.time() < _REDIS_RETRY_UNTIL_TS:
            return None
        try:
            client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                health_check_interval=30,
            )
            client.ping()
            _REDIS_CLIENT = client
            logger.info('agent queue redis connected, key_prefix=%s', _QUEUE_KEY_PREFIX)
            return _REDIS_CLIENT
        except Exception as exc:
            _mark_redis_client_unavailable(exc)
            return None


def _serialize_queue_payload(
    session_id: str,
    user_id: int,
    user_prompt: str,
    attachments: list[dict[str, Any]],
) -> str:
    payload = {
        'session_id': session_id,
        'user_id': user_id,
        'user_prompt': user_prompt,
        'attachments': attachments,
        'queued_at': utcnow().isoformat(),
    }
    return json.dumps(payload, ensure_ascii=False)


def _deserialize_queue_payload(session_id: str, payload_raw: str) -> QueuedAgentRun | None:
    try:
        payload = json.loads(payload_raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    parsed_session_id = str(payload.get('session_id') or '').strip() or session_id
    try:
        user_id = int(payload.get('user_id'))
    except (TypeError, ValueError):
        return None
    user_prompt = str(payload.get('user_prompt') or '')
    attachments_raw = payload.get('attachments')
    attachments = attachments_raw if isinstance(attachments_raw, list) else []

    queued_at = utcnow()
    raw_queued_at = payload.get('queued_at')
    if isinstance(raw_queued_at, str) and raw_queued_at.strip():
        try:
            queued_at = datetime.fromisoformat(raw_queued_at)
        except ValueError:
            queued_at = utcnow()

    return QueuedAgentRun(
        session_id=parsed_session_id,
        user_id=user_id,
        user_prompt=user_prompt,
        attachments=attachments,
        queued_at=queued_at,
    )


def _queue_info_from_snapshot(
    session_id: str,
    queue_session_ids: list[str],
    running_session_id: str | None,
) -> tuple[bool, int]:
    running_count = 1 if running_session_id else 0
    for idx, current_session_id in enumerate(queue_session_ids):
        if current_session_id == session_id:
            return True, running_count + idx
    return False, running_count + len(queue_session_ids)


def _get_agent_queue_info_from_redis(redis_client: Redis, session_id: str) -> tuple[bool, int]:
    queue_session_ids = [str(item) for item in redis_client.lrange(_REDIS_QUEUE_LIST_KEY, 0, -1) if str(item).strip()]
    running_raw = redis_client.get(_REDIS_QUEUE_RUNNING_KEY)
    running_session_id = str(running_raw).strip() if isinstance(running_raw, str) else None
    if running_session_id == '':
        running_session_id = None
    return _queue_info_from_snapshot(session_id, queue_session_ids, running_session_id)


def _get_agent_queue_info_from_db(session_id: str) -> tuple[bool, int]:
    with SessionLocal() as db:
        queued_rows = (
            db.query(AgentSession.id)
            .filter(AgentSession.status == 'queued')
            .order_by(AgentSession.last_activity_at.asc(), AgentSession.created_at.asc(), AgentSession.id.asc())
            .all()
        )
        queued_session_ids = [str(row[0]) for row in queued_rows if row and row[0]]

        running_row = (
            db.query(AgentSession.id)
            .filter(AgentSession.status == 'running')
            .order_by(AgentSession.last_activity_at.asc(), AgentSession.created_at.asc(), AgentSession.id.asc())
            .first()
        )
        running_session_id = str(running_row[0]) if running_row and running_row[0] else None

    return _queue_info_from_snapshot(session_id, queued_session_ids, running_session_id)


def _is_redis_running_session(session_id: str) -> bool:
    redis_client = _get_redis_client()
    if redis_client is None:
        return False
    try:
        running_raw = redis_client.get(_REDIS_QUEUE_RUNNING_KEY)
        return isinstance(running_raw, str) and running_raw.strip() == session_id
    except Exception as exc:
        _mark_redis_client_unavailable(exc)
        return False


def is_agent_session_running(session_id: str) -> bool:
    if _is_redis_running_session(session_id):
        return True

    with SessionLocal() as db:
        row = (
            db.query(AgentSession.id)
            .filter(AgentSession.id == session_id, AgentSession.status == 'running')
            .first()
        )
        return bool(row)


def get_agent_queue_info(session_id: str, user_id: int) -> tuple[bool, int]:
    _ = user_id  # keep signature for existing call sites
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            return _get_agent_queue_info_from_redis(redis_client, session_id)
        except Exception as exc:
            _mark_redis_client_unavailable(exc)
    return _get_agent_queue_info_from_db(session_id)


def _enqueue_agent_run_in_memory(
    session_id: str,
    user_id: int,
    user_prompt: str,
    attachments: list[dict[str, Any]],
) -> int:
    with _QUEUE_COND:
        if session_id in _QUEUED_SESSION_IDS:
            return _count_queue_ahead_users_locked(stop_at_session_id=session_id)

        ahead = _count_queue_ahead_users_locked()
        _QUEUE_ITEMS.append(QueuedAgentRun(
            session_id=session_id,
            user_id=user_id,
            user_prompt=user_prompt,
            attachments=attachments,
            queued_at=utcnow(),
        ))
        _QUEUED_SESSION_IDS.add(session_id)
        _QUEUE_COND.notify_all()
        return ahead


def _enqueue_agent_run_redis(
    redis_client: Redis,
    session_id: str,
    user_id: int,
    user_prompt: str,
    attachments: list[dict[str, Any]],
) -> int:
    payload = _serialize_queue_payload(
        session_id=session_id,
        user_id=user_id,
        user_prompt=user_prompt,
        attachments=attachments,
    )
    redis_client.eval(
        _REDIS_ENQUEUE_SCRIPT,
        2,
        _REDIS_QUEUE_PAYLOADS_KEY,
        _REDIS_QUEUE_LIST_KEY,
        session_id,
        payload,
    )
    queued, ahead = _get_agent_queue_info_from_redis(redis_client, session_id)
    if queued:
        return ahead
    # Redis state had stale payload/list inconsistency; fallback to DB snapshot.
    _, db_ahead = _get_agent_queue_info_from_db(session_id)
    return db_ahead


def enqueue_agent_run(
    session_id: str,
    user_id: int,
    user_prompt: str,
    attachments: list[dict[str, Any]],
) -> int:
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            return _enqueue_agent_run_redis(
                redis_client,
                session_id=session_id,
                user_id=user_id,
                user_prompt=user_prompt,
                attachments=attachments,
            )
        except Exception as exc:
            _mark_redis_client_unavailable(exc)
    return _enqueue_agent_run_in_memory(
        session_id=session_id,
        user_id=user_id,
        user_prompt=user_prompt,
        attachments=attachments,
    )


def _dequeue_agent_run_in_memory(session_id: str) -> bool:
    with _QUEUE_COND:
        if session_id not in _QUEUED_SESSION_IDS:
            return False
        for idx, item in enumerate(_QUEUE_ITEMS):
            if item.session_id != session_id:
                continue
            _QUEUE_ITEMS.pop(idx)
            _QUEUED_SESSION_IDS.discard(session_id)
            _QUEUE_COND.notify_all()
            return True
        _QUEUED_SESSION_IDS.discard(session_id)
        _QUEUE_COND.notify_all()
        return False


def _dequeue_agent_run_redis(redis_client: Redis, session_id: str) -> bool:
    removed = redis_client.eval(
        _REDIS_DEQUEUE_SCRIPT,
        2,
        _REDIS_QUEUE_PAYLOADS_KEY,
        _REDIS_QUEUE_LIST_KEY,
        session_id,
    )
    return bool(int(removed or 0))


def dequeue_agent_run(session_id: str) -> bool:
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            return _dequeue_agent_run_redis(redis_client, session_id)
        except Exception as exc:
            _mark_redis_client_unavailable(exc)
    return _dequeue_agent_run_in_memory(session_id)


def _pop_next_agent_run_redis(redis_client: Redis) -> QueuedAgentRun | None:
    raw = redis_client.eval(
        _REDIS_POP_NEXT_SCRIPT,
        3,
        _REDIS_QUEUE_PAYLOADS_KEY,
        _REDIS_QUEUE_LIST_KEY,
        _REDIS_QUEUE_RUNNING_KEY,
        str(AGENT_QUEUE_RUNNING_TTL_SECONDS),
    )
    if not isinstance(raw, list) or not raw:
        return None
    if raw[0] in {'__BUSY__', '__EMPTY__'}:
        return None
    if len(raw) < 2:
        return None
    session_id = str(raw[0])
    payload_raw = str(raw[1])
    run = _deserialize_queue_payload(session_id, payload_raw)
    if run is not None:
        return run
    _clear_redis_running_session(session_id)
    return None


def _touch_redis_running_session(session_id: str) -> None:
    redis_client = _get_redis_client()
    if redis_client is None:
        return
    try:
        redis_client.eval(
            _REDIS_TOUCH_RUNNING_SCRIPT,
            1,
            _REDIS_QUEUE_RUNNING_KEY,
            session_id,
            str(AGENT_QUEUE_RUNNING_TTL_SECONDS),
        )
    except Exception as exc:
        _mark_redis_client_unavailable(exc)


def _clear_redis_running_session(session_id: str) -> None:
    redis_client = _get_redis_client()
    if redis_client is None:
        return
    try:
        redis_client.eval(
            _REDIS_CLEAR_RUNNING_SCRIPT,
            1,
            _REDIS_QUEUE_RUNNING_KEY,
            session_id,
        )
    except Exception as exc:
        _mark_redis_client_unavailable(exc)


def _redis_running_heartbeat_loop(session_id: str, stop_event: threading.Event) -> None:
    while not stop_event.wait(AGENT_QUEUE_RUNNING_HEARTBEAT_SECONDS):
        _touch_redis_running_session(session_id)


def _dequeue_next_run_locked() -> tuple[QueuedAgentRun | None, int | None, float | None]:
    global _RUNNING_SESSION_ID, _ACTIVE_OWNER_USER_ID, _OWNER_GRACE_UNTIL

    now = utcnow()
    if _ACTIVE_OWNER_USER_ID is not None and _OWNER_GRACE_UNTIL is not None:
        if now < _OWNER_GRACE_UNTIL:
            for idx, item in enumerate(_QUEUE_ITEMS):
                if item.user_id == _ACTIVE_OWNER_USER_ID:
                    selected = _QUEUE_ITEMS.pop(idx)
                    _QUEUED_SESSION_IDS.discard(selected.session_id)
                    _RUNNING_SESSION_ID = selected.session_id
                    return selected, None, None

            wait_seconds = max(0.0, (_OWNER_GRACE_UNTIL - now).total_seconds())
            return None, None, wait_seconds
        else:
            expired_owner = _ACTIVE_OWNER_USER_ID
            _ACTIVE_OWNER_USER_ID = None
            _OWNER_GRACE_UNTIL = None
            return None, expired_owner, None

    if not _QUEUE_ITEMS:
        return None, None, None

    selected = _QUEUE_ITEMS.pop(0)
    _QUEUED_SESSION_IDS.discard(selected.session_id)
    _RUNNING_SESSION_ID = selected.session_id
    _ACTIVE_OWNER_USER_ID = selected.user_id
    return selected, None, None


def _run_agent_once(session_id: str, user_prompt: str, attachments: list[dict[str, Any]]) -> None:
    AGENT_RUN_LOCK.acquire()
    heartbeat_stop_event: threading.Event | None = None
    heartbeat_thread: threading.Thread | None = None

    if _is_redis_running_session(session_id):
        _touch_redis_running_session(session_id)
        heartbeat_stop_event = threading.Event()
        heartbeat_thread = threading.Thread(
            target=_redis_running_heartbeat_loop,
            args=(session_id, heartbeat_stop_event),
            daemon=True,
            name=f'agent-redis-heartbeat-{session_id[:8]}',
        )
        heartbeat_thread.start()

    try:
        with SessionLocal() as db:
            session = db.get(AgentSession, session_id)
            if not session:
                return
            task = db.get(Task, session.task_id)
            if _task_is_terminal(task):
                session.status = 'idle'
                session.last_error = None
                session.last_activity_at = utcnow()
                db.add(session)
                create_agent_message(
                    db,
                    session_id=session_id,
                    role='system',
                    content='任务已结束，已取消排队请求。',
                )
                db.commit()
                return

            session.status = 'running'
            session.last_error = None
            session.last_activity_at = utcnow()
            db.add(session)
            db.commit()

            if _is_cancel_requested(session_id):
                session.status = 'idle'
                session.last_error = None
                session.last_activity_at = utcnow()
                db.add(session)
                create_agent_message(db, session_id=session_id, role='system', content='已中断当前执行。')
                db.commit()
                return

            _prepare_container_for_session(db, session)

            if _is_cancel_requested(session_id):
                session = db.get(AgentSession, session_id)
                if not session:
                    return
                session.status = 'idle'
                session.last_error = None
                session.last_activity_at = utcnow()
                db.add(session)
                create_agent_message(db, session_id=session_id, role='system', content='已中断当前执行。')
                db.commit()
                return

            prompt = _build_prompt(user_prompt, attachments)
            prompt_quoted = shlex.quote(prompt)
            kimi_session_quoted = shlex.quote(session.kimi_session_id)
            env_file_hint = str(AGENT_ENV_FILE)
            cmd = [
                'docker',
                'exec',
                '-i',
                session.container_id,
                'bash',
                '-lc',
                f'cd /workspace && source /config.sh; '
                'KIMI_BIN="${KIMI_CLI_BIN:-}"; '
                'if [ -z "$KIMI_BIN" ]; then '
                'if command -v kimi >/dev/null 2>&1; then KIMI_BIN="$(command -v kimi)"; '
                'elif command -v kimi-code >/dev/null 2>&1; then KIMI_BIN="$(command -v kimi-code)"; '
                'fi; '
                'fi; '
                'if [ -z "$KIMI_BIN" ]; then '
                f'echo "{AGENT_ERROR_PREFIX} Kimi CLI 未安装或不在 PATH。请在 agent-sandbox:cn 镜像中安装 kimi，'
                f'或在 {env_file_hint} 设置 KIMI_CLI_BIN=/path/to/kimi"; '
                'exit 127; '
                'fi; '
                f'"$KIMI_BIN" --print -p {prompt_quoted} --output-format=stream-json --session {kimi_session_quoted}',
            ]

            popen_kwargs: dict[str, Any] = {
                'stdin': subprocess.PIPE,
                'stdout': subprocess.PIPE,
                'stderr': subprocess.STDOUT,
                'text': True,
                'encoding': PROCESS_ENCODING,
                'errors': 'replace',
                'bufsize': 1,
            }
            if os.name == 'nt':
                popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

            process = subprocess.Popen(cmd, **popen_kwargs)
            _register_running_exec(session.id, str(session.container_id or ''), process)

            has_explicit_agent_error = False
            return_code = -1
            try:
                if process.stdout:
                    for raw in process.stdout:
                        line = raw.strip()
                        if not line:
                            continue
                        if line.startswith(AGENT_ERROR_PREFIX):
                            has_explicit_agent_error = True
                        _persist_stream_line(db, session_id, line)

                return_code = process.wait()
            finally:
                _unregister_running_exec(session.id)

            session = db.get(AgentSession, session_id)
            if not session:
                return

            cancel_requested = _take_cancel_requested(session_id)
            task = db.get(Task, session.task_id)
            task_terminal = _task_is_terminal(task)
            session.last_activity_at = utcnow()
            if return_code == 0 or cancel_requested or task_terminal:
                session.status = 'idle'
                session.last_error = None
                if cancel_requested:
                    create_agent_message(
                        db,
                        session_id=session_id,
                        role='system',
                        content='已中断当前执行。',
                    )
            else:
                session.status = 'error'
                if has_explicit_agent_error:
                    session.last_error = 'Kimi CLI 不可用，请联系管理员检查容器镜像或 KIMI_CLI_BIN 配置'
                else:
                    session.last_error = f'代理进程异常退出（code={return_code}）'
                    create_agent_message(
                        db,
                        session_id=session_id,
                        role='system',
                        content='代理执行失败，请稍后重试。',
                    )

            if session.interaction_count >= session.max_interactions and session.container_id:
                _stop_container(session.container_id)
                cleanup_workspace_keep_deliverables(session.user_id, session.id)
                session.container_id = None

            db.add(session)
            db.commit()
    except Exception as exc:
        logger.exception('agent run failed session=%s', session_id)
        _unregister_running_exec(session_id)
        if _take_cancel_requested(session_id):
            with SessionLocal() as db:
                session = db.get(AgentSession, session_id)
                if session:
                    session.status = 'idle'
                    session.last_error = None
                    session.last_activity_at = utcnow()
                    db.add(session)
                create_agent_message(db, session_id=session_id, role='system', content='已中断当前执行。')
                db.commit()
        else:
            _append_system_error(session_id, f'代理执行失败：{exc}')
    finally:
        if heartbeat_stop_event is not None:
            heartbeat_stop_event.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=1)
        _clear_redis_running_session(session_id)
        _take_cancel_requested(session_id)
        AGENT_RUN_LOCK.release()


def _agent_queue_loop() -> None:
    global _RUNNING_SESSION_ID, _OWNER_GRACE_UNTIL

    while True:
        redis_client = _get_redis_client()
        if redis_client is not None:
            try:
                next_run = _pop_next_agent_run_redis(redis_client)
            except Exception as exc:
                _mark_redis_client_unavailable(exc)
                time.sleep(AGENT_QUEUE_REDIS_POLL_SECONDS)
                continue

            if not next_run:
                time.sleep(AGENT_QUEUE_REDIS_POLL_SECONDS)
                continue

            _run_agent_once(
                session_id=next_run.session_id,
                user_prompt=next_run.user_prompt,
                attachments=next_run.attachments,
            )
            continue

        next_run: QueuedAgentRun | None = None
        expired_owner: int | None = None
        wait_seconds: float | None = None

        with _QUEUE_COND:
            next_run, expired_owner, wait_seconds = _dequeue_next_run_locked()
            if next_run is None and expired_owner is None:
                if wait_seconds is None:
                    _QUEUE_COND.wait(timeout=AGENT_QUEUE_REDIS_POLL_SECONDS)
                else:
                    _QUEUE_COND.wait(timeout=min(wait_seconds, AGENT_QUEUE_REDIS_POLL_SECONDS))
                continue

        if expired_owner is not None:
            cleaned = _cleanup_user_idle_containers(expired_owner)
            if cleaned:
                logger.info('cleaned %s idle container(s) for expired owner user=%s', cleaned, expired_owner)
            continue

        if not next_run:
            continue

        _run_agent_once(
            session_id=next_run.session_id,
            user_prompt=next_run.user_prompt,
            attachments=next_run.attachments,
        )

        with _QUEUE_COND:
            _RUNNING_SESSION_ID = None
            if _ACTIVE_OWNER_USER_ID == next_run.user_id:
                _OWNER_GRACE_UNTIL = utcnow() + timedelta(seconds=AGENT_QUEUE_GRACE_SECONDS)
            _QUEUE_COND.notify_all()


def start_agent_queue_daemon() -> None:
    global _QUEUE_WORKER_STARTED
    with _QUEUE_LOCK:
        if _QUEUE_WORKER_STARTED:
            return
        _QUEUE_WORKER_STARTED = True
    thread = threading.Thread(target=_agent_queue_loop, daemon=True, name='agent-queue-worker')
    thread.start()


def spawn_agent_run(
    session_id: str,
    user_id: int,
    user_prompt: str,
    attachments: list[dict[str, Any]],
) -> int:
    start_agent_queue_daemon()
    return enqueue_agent_run(
        session_id=session_id,
        user_id=user_id,
        user_prompt=user_prompt,
        attachments=attachments,
    )


def list_deliverables(user_id: int, session_id: str) -> list[dict[str, Any]]:
    root = deliverables_dir(user_id, session_id)
    if not root.exists():
        return []

    out: list[dict[str, Any]] = []
    for file in root.rglob('*'):
        if not file.is_file():
            continue
        rel = file.relative_to(root).as_posix()
        stat = file.stat()
        out.append({
            'name': rel,
            'size': int(stat.st_size),
            'updated_at': datetime.utcfromtimestamp(stat.st_mtime),
        })
    out.sort(key=lambda x: x['updated_at'], reverse=True)
    return out


def resolve_deliverable_path(user_id: int, session_id: str, relative_name: str) -> Path:
    root = deliverables_dir(user_id, session_id).resolve()
    target = (root / relative_name).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError('invalid file path')
    if not target.is_file():
        raise FileNotFoundError('file not found')
    return target


def delete_deliverables(user_id: int, session_id: str, names: list[str]) -> list[str]:
    """Delete named deliverables. Returns list of successfully deleted names."""
    deleted: list[str] = []
    for name in names:
        try:
            path = resolve_deliverable_path(user_id, session_id, name)
            path.unlink()
            deleted.append(name)
        except (ValueError, FileNotFoundError):
            pass
    return deleted


def zip_deliverables(user_id: int, session_id: str, names: list[str] | None = None) -> bytes:
    """Create a zip archive of deliverables. If names is None/empty, zip all files."""
    root = deliverables_dir(user_id, session_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        if names:
            for name in names:
                try:
                    path = resolve_deliverable_path(user_id, session_id, name)
                    zf.write(path, name)
                except (ValueError, FileNotFoundError):
                    pass
        elif root.exists():
            for file in root.rglob('*'):
                if file.is_file():
                    rel = file.relative_to(root).as_posix()
                    zf.write(file, rel)
    return buf.getvalue()


def cleanup_idle_agent_containers(idle_minutes: int = AGENT_IDLE_TTL_MINUTES) -> int:
    threshold = utcnow() - timedelta(minutes=idle_minutes)
    cleaned = 0
    with SessionLocal() as db:
        sessions = (
            db.query(AgentSession)
            .filter(
                AgentSession.container_id.isnot(None),
                AgentSession.status != 'running',
                AgentSession.last_activity_at <= threshold,
            )
            .all()
        )
        for session in sessions:
            _stop_container(session.container_id)
            cleanup_workspace_keep_deliverables(session.user_id, session.id)
            session.container_id = None
            if session.status != 'queued':
                session.status = 'idle'
            session.last_error = None
            db.add(session)
            cleaned += 1
        if cleaned:
            db.commit()
    return cleaned


def _cleanup_loop() -> None:
    while True:
        try:
            cleaned = cleanup_idle_agent_containers()
            if cleaned:
                logger.info('cleaned %s idle agent container(s)', cleaned)
        except Exception:
            logger.exception('agent cleanup loop error')
        time.sleep(60)


def start_agent_cleanup_daemon() -> None:
    global _CLEANER_STARTED
    start_agent_queue_daemon()
    with _CLEANER_LOCK:
        if _CLEANER_STARTED:
            return
        _CLEANER_STARTED = True
        thread = threading.Thread(target=_cleanup_loop, daemon=True, name='agent-cleaner')
        thread.start()
