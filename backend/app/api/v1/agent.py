import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_admin, require_completed_user
from app.db.session import get_db
from app.models.agent import AgentMessage, AgentSession
from app.models.enums import TaskStatus
from app.models.moderation import AdminActionLog
from app.models.task import Task, TaskCategory
from app.models.user import User
from app.schemas.agent import (
    AgentAdminConfigOut,
    AgentAdminConfigUpdate,
    AgentAdminSessionItem,
    AgentAdminSessionListOut,
    AgentAvailabilityOut,
    AgentBatchGrantOut,
    AgentBatchGrantRequest,
    AgentCancelOut,
    AgentDeliverableDeleteBody,
    AgentDeliverableDeleteOut,
    AgentDeliverableOut,
    AgentMessageOut,
    AgentMySessionItem,
    AgentMySessionListOut,
    AgentSendOut,
    AgentSessionDetailOut,
    AgentStartOut,
)
from app.services.agent_service import (
    MAX_AGENT_FILE_SIZE,
    MAX_AGENT_FILES_PER_MESSAGE,
    MAX_AGENT_INTERACTIONS,
    create_agent_message,
    dequeue_agent_run,
    delete_deliverables,
    ensure_session_workspace,
    get_agent_queue_info,
    is_agent_session_running,
    interrupt_agent_session,
    list_deliverables,
    release_session_container_now,
    resolve_deliverable_path,
    resolve_unique_upload_name,
    sanitize_cli_risky_prompt,
    spawn_agent_run,
    uploads_dir,
    zip_deliverables,
)
from app.services.auth_service import get_agent_enabled, set_agent_enabled
from app.utils.user_display import display_name

router = APIRouter(prefix='/agent', tags=['agent'])


_TERMINAL_TASK_STATUSES = {'completed', 'canceled'}


def _normalize_queued_status(db: Session, session: AgentSession) -> AgentSession:
    if session.status != 'queued':
        return session
    queued, _ = get_agent_queue_info(session.id, session.user_id)
    if queued or is_agent_session_running(session.id):
        return session
    session.status = 'idle'
    session.last_error = None
    session.last_activity_at = datetime.utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _can_send(session: AgentSession, task: Task) -> bool:
    if task.status in _TERMINAL_TASK_STATUSES:
        return False
    return session.interaction_count < session.max_interactions and session.status not in {'running', 'queued'}


def _session_to_start_out(session: AgentSession, task: Task, remaining_count: int) -> AgentStartOut:
    queued, queue_ahead_users = get_agent_queue_info(session.id, session.user_id)
    queue_waiting = queued or queue_ahead_users > 0
    return AgentStartOut(
        session_id=session.id,
        task_id=task.id,
        task_title=task.title,
        task_status=task.status,
        status=session.status,
        interaction_count=session.interaction_count,
        max_interactions=session.max_interactions,
        remaining_count=remaining_count,
        can_send=_can_send(session, task),
        queue_waiting=queue_waiting,
        queue_ahead_users=queue_ahead_users,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _session_to_detail_out(session: AgentSession, task: Task, remaining_count: int) -> AgentSessionDetailOut:
    queued, queue_ahead_users = get_agent_queue_info(session.id, session.user_id)
    queue_waiting = queued or queue_ahead_users > 0
    return AgentSessionDetailOut(
        session_id=session.id,
        task_id=task.id,
        task_title=task.title,
        task_status=task.status,
        status=session.status,
        interaction_count=session.interaction_count,
        max_interactions=session.max_interactions,
        remaining_count=remaining_count,
        can_send=_can_send(session, task),
        queue_waiting=queue_waiting,
        queue_ahead_users=queue_ahead_users,
        created_at=session.created_at,
        updated_at=session.updated_at,
        deliverables=[AgentDeliverableOut(**item) for item in list_deliverables(session.user_id, session.id)],
    )


def _message_to_out(msg: AgentMessage) -> AgentMessageOut:
    attachments = []
    if msg.attachments_json:
        try:
            parsed = json.loads(msg.attachments_json)
            if isinstance(parsed, list):
                attachments = parsed
        except (json.JSONDecodeError, ValueError):
            attachments = []
    return AgentMessageOut(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        tool_name=msg.tool_name,
        tool_arguments=msg.tool_arguments,
        tool_call_id=msg.tool_call_id,
        attachments=attachments,
        created_at=msg.created_at,
    )


def _parse_message_attachments(msg: AgentMessage | None) -> list[dict]:
    if not msg or not msg.attachments_json:
        return []
    try:
        parsed = json.loads(msg.attachments_json)
    except (json.JSONDecodeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _resolve_upload_path(user_id: int, session_id: str, relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    root = uploads_dir(user_id, session_id).resolve()
    candidate = (root.parent / relative_path).resolve()
    if not str(candidate).startswith(str(root.parent)):
        return None
    return candidate


def _delete_message_uploads(user_id: int, session_id: str, attachments: list[dict]) -> None:
    for att in attachments:
        path = _resolve_upload_path(user_id, session_id, str(att.get('workspace_path') or ''))
        if not path:
            continue
        try:
            path.unlink(missing_ok=True)
        except Exception:
            continue


def _rollback_queued_user_message(db: Session, session: AgentSession, user: User) -> tuple[int | None, str | None, list[dict]]:
    latest_user_message = (
        db.query(AgentMessage)
        .filter(AgentMessage.session_id == session.id, AgentMessage.role == 'user')
        .order_by(desc(AgentMessage.id))
        .first()
    )
    if not latest_user_message:
        return None, None, []

    removed_message_id = int(latest_user_message.id)
    restored_content = latest_user_message.content or ''
    attachments = _parse_message_attachments(latest_user_message)
    _delete_message_uploads(user.id, session.id, attachments)
    db.delete(latest_user_message)

    if int(session.interaction_count or 0) > 0:
        session.interaction_count = int(session.interaction_count or 0) - 1

    session.status = 'idle'
    session.last_error = None
    session.last_activity_at = datetime.utcnow()
    db.add(session)
    return removed_message_id, restored_content, attachments


def _get_owned_session(db: Session, user_id: int, session_id: str) -> AgentSession:
    session = db.get(AgentSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail='代理会话不存在')
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail='无权限访问该代理会话')
    return session


@router.get('/me/availability', response_model=AgentAvailabilityOut)
def get_my_agent_availability(
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> AgentAvailabilityOut:
    return AgentAvailabilityOut(
        agent_enabled=get_agent_enabled(db),
        remaining_count=int(user.agent_usage_remaining or 0),
        max_interactions=MAX_AGENT_INTERACTIONS,
        max_files=MAX_AGENT_FILES_PER_MESSAGE,
        max_file_size_mb=MAX_AGENT_FILE_SIZE // (1024 * 1024),
    )


@router.get('/me/sessions', response_model=AgentMySessionListOut)
def list_my_agent_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> AgentMySessionListOut:
    query = (
        db.query(AgentSession, Task)
        .join(Task, Task.id == AgentSession.task_id)
        .filter(AgentSession.user_id == user.id)
    )
    total = query.count()
    rows = (
        query
        .order_by(desc(AgentSession.updated_at), desc(AgentSession.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        AgentMySessionItem(
            session_id=s.id,
            task_id=t.id,
            task_title=t.title,
            task_status=t.status,
            status=s.status,
            interaction_count=s.interaction_count,
            max_interactions=s.max_interactions,
            can_send=_can_send(s, t),
            last_activity_at=s.last_activity_at,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s, t in rows
    ]
    return AgentMySessionListOut(total=total, page=page, page_size=page_size, items=items)


@router.post('/tasks/{task_id}/start', response_model=AgentStartOut)
def start_task_agent(
    task_id: int,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> AgentStartOut:
    if not get_agent_enabled(db):
        raise HTTPException(status_code=403, detail='AI 代理功能当前已关闭')

    task = db.get(Task, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail='任务不存在')
    if task.publisher_id != user.id:
        raise HTTPException(status_code=403, detail='仅发布者可开启 AI 代理')
    if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELED):
        raise HTTPException(status_code=400, detail='任务已结束，无法开启 AI 代理')

    category = db.get(TaskCategory, task.category_id) if task.category_id else None
    if not category or not category.ai_agent_enabled:
        raise HTTPException(status_code=400, detail='该任务类别未开启 AI 代理')

    if task.assignee_id and task.assignee_id != user.id:
        raise HTTPException(status_code=400, detail='任务已有接单者，无法开启 AI 代理')

    existing: AgentSession | None = None
    if task.agent_session_id:
        linked = db.get(AgentSession, task.agent_session_id)
        if linked and linked.user_id == user.id:
            existing = linked
    if not existing:
        existing = (
            db.query(AgentSession)
            .filter(AgentSession.task_id == task.id, AgentSession.user_id == user.id)
            .order_by(desc(AgentSession.created_at))
            .first()
        )

    if existing:
        if task.status == TaskStatus.OPEN:
            task.status = TaskStatus.IN_PROGRESS
        task.assignee_id = None
        if task.agent_session_id != existing.id:
            task.agent_session_id = existing.id
        db.add(task)
        db.commit()
        db.refresh(task)
        ensure_session_workspace(user.id, existing.id)
        return _session_to_start_out(existing, task, int(user.agent_usage_remaining or 0))

    if int(user.agent_usage_remaining or 0) <= 0:
        raise HTTPException(status_code=403, detail='AI 代理次数不足，请联系管理员发放')

    session = AgentSession(
        id=str(uuid.uuid4()),
        task_id=task.id,
        user_id=user.id,
        kimi_session_id=str(uuid.uuid4()),
        status='idle',
        interaction_count=0,
        max_interactions=MAX_AGENT_INTERACTIONS,
        last_activity_at=datetime.utcnow(),
    )
    db.add(session)

    user.agent_usage_remaining = max(0, int(user.agent_usage_remaining or 0) - 1)
    task.status = TaskStatus.IN_PROGRESS
    task.assignee_id = None
    task.agent_session_id = session.id
    db.add(user)
    db.add(task)
    db.commit()
    db.refresh(session)
    db.refresh(task)

    ensure_session_workspace(user.id, session.id)
    return _session_to_start_out(session, task, int(user.agent_usage_remaining or 0))


@router.get('/sessions/{session_id}', response_model=AgentSessionDetailOut)
def get_agent_session(
    session_id: str,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> AgentSessionDetailOut:
    session = _normalize_queued_status(db, _get_owned_session(db, user.id, session_id))
    task = db.get(Task, session.task_id)
    if not task:
        raise HTTPException(status_code=404, detail='关联任务不存在')
    return _session_to_detail_out(session, task, int(user.agent_usage_remaining or 0))


@router.get('/sessions/{session_id}/messages', response_model=list[AgentMessageOut])
def list_agent_messages(
    session_id: str,
    after_id: int = Query(default=0, ge=0),
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> list[AgentMessageOut]:
    _get_owned_session(db, user.id, session_id)
    rows = (
        db.query(AgentMessage)
        .filter(AgentMessage.session_id == session_id, AgentMessage.id > after_id)
        .order_by(AgentMessage.id.asc())
        .limit(500)
        .all()
    )
    return [_message_to_out(row) for row in rows]


@router.post('/sessions/{session_id}/messages', response_model=AgentSendOut)
async def send_agent_message(
    session_id: str,
    content: str = Form(default=''),
    files: list[UploadFile] = File(default=[]),
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> AgentSendOut:
    if not get_agent_enabled(db):
        raise HTTPException(status_code=403, detail='AI 代理功能当前已关闭')

    session = _normalize_queued_status(db, _get_owned_session(db, user.id, session_id))
    task = db.get(Task, session.task_id)
    if not task:
        raise HTTPException(status_code=404, detail='关联任务不存在')
    if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELED):
        raise HTTPException(status_code=400, detail='任务已结束，无法继续发送')
    if session.status in {'running', 'queued'}:
        raise HTTPException(status_code=409, detail='代理正在处理中，请稍后再发送')
    if session.interaction_count >= session.max_interactions:
        if release_session_container_now(db, session):
            db.commit()
        raise HTTPException(status_code=400, detail='当前代理会话交互次数已达上限，请重新开启代理')

    text = sanitize_cli_risky_prompt(content)
    if not text and not files:
        raise HTTPException(status_code=422, detail='请输入需求描述或上传文件')
    if len(files) > MAX_AGENT_FILES_PER_MESSAGE:
        raise HTTPException(status_code=400, detail=f'单次最多上传 {MAX_AGENT_FILES_PER_MESSAGE} 个文件')

    ensure_session_workspace(user.id, session.id)
    target_dir = uploads_dir(user.id, session.id)
    target_dir.mkdir(parents=True, exist_ok=True)

    attachment_items: list[dict] = []
    seen_names: set[str] = set()
    for upload in files:
        raw = await upload.read(MAX_AGENT_FILE_SIZE + 1)
        if len(raw) > MAX_AGENT_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f'文件「{upload.filename or "未命名文件"}」超过 50 MB 限制',
            )
        original = upload.filename or 'unnamed'
        stored = resolve_unique_upload_name(target_dir, original, seen_names)
        (target_dir / stored).write_bytes(raw)
        attachment_items.append({
            'name': original,
            'stored_name': stored,
            'workspace_path': f'uploads/{stored}',
            'size': len(raw),
        })

    display_content = text or f'上传了 {len(attachment_items)} 个文件，请处理。'
    create_agent_message(
        db,
        session_id=session.id,
        role='user',
        content=display_content,
        attachments=attachment_items,
    )

    session.interaction_count = int(session.interaction_count or 0) + 1
    session.status = 'queued'
    session.last_activity_at = datetime.utcnow()
    db.add(session)
    db.commit()

    queue_ahead_users = spawn_agent_run(
        session.id,
        session.user_id,
        user_prompt=text or '请先查看我上传的文件，然后继续完成任务。',
        attachments=attachment_items,
    )

    return AgentSendOut(
        queued=True,
        queue_ahead_users=queue_ahead_users,
        interaction_count=session.interaction_count,
        max_interactions=session.max_interactions,
    )


@router.post('/sessions/{session_id}/cancel', response_model=AgentCancelOut)
def cancel_running_agent_session(
    session_id: str,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> AgentCancelOut:
    session = _get_owned_session(db, user.id, session_id)
    task = db.get(Task, session.task_id)
    if not task:
        raise HTTPException(status_code=404, detail='关联任务不存在')
    if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELED):
        return AgentCancelOut(canceled=False, mode='none')

    if session.status == 'queued':
        dequeued = dequeue_agent_run(session.id)
        if dequeued:
            removed_message_id, restored_content, restored_attachments = _rollback_queued_user_message(db, session, user)
            db.commit()
            return AgentCancelOut(
                canceled=True,
                mode='queued',
                removed_message_id=removed_message_id,
                restored_content=restored_content,
                restored_attachments=restored_attachments,
            )

        db.refresh(session)

    if session.status != 'running':
        return AgentCancelOut(canceled=False, mode='none')

    canceled = interrupt_agent_session(db, session)
    if canceled:
        db.commit()
    return AgentCancelOut(canceled=canceled, mode='running' if canceled else 'none')


@router.get('/sessions/{session_id}/deliverables', response_model=list[AgentDeliverableOut])
def get_deliverables(
    session_id: str,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> list[AgentDeliverableOut]:
    _get_owned_session(db, user.id, session_id)
    return [AgentDeliverableOut(**item) for item in list_deliverables(user.id, session_id)]


@router.get('/sessions/{session_id}/deliverables/file')
def download_deliverable(
    session_id: str,
    name: str = Query(min_length=1),
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
):
    _get_owned_session(db, user.id, session_id)
    try:
        target = resolve_deliverable_path(user.id, session_id, name)
    except ValueError:
        raise HTTPException(status_code=400, detail='非法文件路径')
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='文件不存在')
    return FileResponse(path=str(target), filename=target.name)


@router.get('/sessions/{session_id}/deliverables/zip')
def download_deliverables_zip(
    session_id: str,
    names: list[str] = Query(default=[]),
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
):
    from fastapi.responses import Response
    _get_owned_session(db, user.id, session_id)
    data = zip_deliverables(user.id, session_id, names or None)
    return Response(
        content=data,
        media_type='application/zip',
        headers={'Content-Disposition': 'attachment; filename="deliverables.zip"'},
    )


@router.delete('/sessions/{session_id}/deliverables', response_model=AgentDeliverableDeleteOut)
def delete_session_deliverables(
    session_id: str,
    payload: AgentDeliverableDeleteBody,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> AgentDeliverableDeleteOut:
    _get_owned_session(db, user.id, session_id)
    deleted = delete_deliverables(user.id, session_id, payload.names)
    return AgentDeliverableDeleteOut(deleted=deleted)


@router.get('/admin/config', response_model=AgentAdminConfigOut)
def get_admin_agent_config(
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AgentAdminConfigOut:
    return AgentAdminConfigOut(agent_enabled=get_agent_enabled(db))


@router.put('/admin/config', response_model=AgentAdminConfigOut)
def update_admin_agent_config(
    payload: AgentAdminConfigUpdate,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AgentAdminConfigOut:
    enabled = set_agent_enabled(db, payload.agent_enabled)
    db.add(AdminActionLog(
        admin_identifier=admin.admin_account or 'admin',
        action='set_agent_enabled',
        target_type='system',
        target_id='platform_setting',
        detail=f'agent_enabled={enabled}',
    ))
    db.commit()
    return AgentAdminConfigOut(agent_enabled=enabled)


@router.post('/admin/grant', response_model=AgentBatchGrantOut)
def batch_grant_agent_usage(
    payload: AgentBatchGrantRequest,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AgentBatchGrantOut:
    user_ids = sorted({uid for uid in payload.user_ids if uid > 0})
    if not payload.include_all and not user_ids:
        raise HTTPException(status_code=422, detail='用户列表不能为空')

    query = db.query(User)
    if not payload.include_all:
        query = query.filter(User.id.in_(user_ids))

    if payload.mode == 'set':
        updated_count = int(query.update(
            {User.agent_usage_remaining: int(payload.amount)},
            synchronize_session=False,
        ) or 0)
        action = 'set_agent_usage'
    else:
        updated_count = int(query.update(
            {User.agent_usage_remaining: func.coalesce(User.agent_usage_remaining, 0) + int(payload.amount)},
            synchronize_session=False,
        ) or 0)
        action = 'grant_agent_usage'

    db.add(AdminActionLog(
        admin_identifier=admin.admin_account or 'admin',
        action=action,
        target_type='user_batch',
        target_id='all_users' if payload.include_all else ','.join(str(uid) for uid in user_ids[:100]),
        detail=(
            f'count={updated_count}, '
            f'mode={payload.mode}, '
            f'amount={payload.amount}, '
            f'include_all={int(payload.include_all)}'
        ),
    ))
    db.commit()
    return AgentBatchGrantOut(updated_user_count=updated_count)


@router.get('/admin/sessions', response_model=AgentAdminSessionListOut)
def list_admin_agent_sessions(
    q: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AgentAdminSessionListOut:
    query = db.query(AgentSession, Task, User).join(Task, Task.id == AgentSession.task_id).join(User, User.id == AgentSession.user_id)
    if user_id:
        query = query.filter(AgentSession.user_id == user_id)
    if q and q.strip():
        like = f'%{q.strip()}%'
        query = query.filter(
            or_(
                Task.title.like(like),
                User.account.like(like),
                User.name.like(like),
                User.nickname.like(like),
            )
        )

    total = query.count()
    rows = (
        query
        .order_by(desc(AgentSession.updated_at), desc(AgentSession.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        AgentAdminSessionItem(
            session_id=s.id,
            task_id=t.id,
            task_title=t.title,
            user_id=u.id,
            user_display_name=display_name(u),
            status=s.status,
            interaction_count=s.interaction_count,
            max_interactions=s.max_interactions,
            has_container=bool(s.container_id),
            last_activity_at=s.last_activity_at,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s, t, u in rows
    ]

    return AgentAdminSessionListOut(total=total, page=page, page_size=page_size, items=items)


@router.get('/admin/sessions/{session_id}/messages', response_model=list[AgentMessageOut])
def list_admin_agent_messages(
    session_id: str,
    after_id: int = Query(default=0, ge=0),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AgentMessageOut]:
    exists = db.get(AgentSession, session_id)
    if not exists:
        raise HTTPException(status_code=404, detail='代理会话不存在')
    rows = (
        db.query(AgentMessage)
        .filter(AgentMessage.session_id == session_id, AgentMessage.id > after_id)
        .order_by(AgentMessage.id.asc())
        .limit(500)
        .all()
    )
    return [_message_to_out(row) for row in rows]
