import json
import logging
import re
import shlex
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.agent import AgentMessage, AgentSession

logger = logging.getLogger(__name__)

MAX_AGENT_FILES_PER_MESSAGE = 5
MAX_AGENT_FILE_SIZE = 50 * 1024 * 1024
MAX_AGENT_INTERACTIONS = 8
AGENT_IDLE_TTL_MINUTES = 20
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
    prompt = user_prompt.strip()
    if not attachments:
        return prompt

    lines = ['']
    lines.append('用户本次上传了文件，可在 /workspace 下直接读取：')
    for att in attachments:
        path = att.get('workspace_path') or att.get('stored_name') or att.get('name')
        original = att.get('name') or ''
        lines.append(f'- {path} (原名: {original})')
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


def _run_agent_once(session_id: str, user_prompt: str, attachments: list[dict[str, Any]]) -> None:
    if not AGENT_RUN_LOCK.acquire(blocking=False):
        _append_system_error(session_id, '当前代理繁忙，请稍后重试。')
        return

    try:
        with SessionLocal() as db:
            session = db.get(AgentSession, session_id)
            if not session:
                return
            session.status = 'running'
            session.last_error = None
            session.last_activity_at = utcnow()
            db.add(session)
            db.commit()

            _prepare_container_for_session(db, session)

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

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=PROCESS_ENCODING,
                errors='replace',
                bufsize=1,
            )

            has_explicit_agent_error = False
            if process.stdout:
                for raw in process.stdout:
                    line = raw.strip()
                    if not line:
                        continue
                    if line.startswith(AGENT_ERROR_PREFIX):
                        has_explicit_agent_error = True
                    _persist_stream_line(db, session_id, line)

            return_code = process.wait()
            session = db.get(AgentSession, session_id)
            if not session:
                return

            session.last_activity_at = utcnow()
            if return_code == 0:
                session.status = 'idle'
                session.last_error = None
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
            db.add(session)
            db.commit()
    except Exception as exc:
        logger.exception('agent run failed session=%s', session_id)
        _append_system_error(session_id, f'代理执行失败：{exc}')
    finally:
        AGENT_RUN_LOCK.release()


def spawn_agent_run(session_id: str, user_prompt: str, attachments: list[dict[str, Any]]) -> None:
    thread = threading.Thread(
        target=_run_agent_once,
        args=(session_id, user_prompt, attachments),
        daemon=True,
        name=f'agent-run-{session_id}',
    )
    thread.start()


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
    with _CLEANER_LOCK:
        if _CLEANER_STARTED:
            return
        _CLEANER_STARTED = True
        thread = threading.Thread(target=_cleanup_loop, daemon=True, name='agent-cleaner')
        thread.start()
