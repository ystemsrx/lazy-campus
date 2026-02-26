import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc, or_
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
    AgentDeliverableOut,
    AgentMessageOut,
    AgentSendOut,
    AgentSessionDetailOut,
    AgentStartOut,
)
from app.services.agent_service import (
    MAX_AGENT_FILE_SIZE,
    MAX_AGENT_FILES_PER_MESSAGE,
    MAX_AGENT_INTERACTIONS,
    create_agent_message,
    ensure_session_workspace,
    is_agent_busy,
    list_deliverables,
    resolve_deliverable_path,
    safe_filename,
    spawn_agent_run,
    uploads_dir,
)
from app.services.auth_service import get_agent_enabled, set_agent_enabled
from app.utils.user_display import display_name

router = APIRouter(prefix='/agent', tags=['agent'])


def _session_to_start_out(session: AgentSession, task: Task, remaining_count: int) -> AgentStartOut:
    return AgentStartOut(
        session_id=session.id,
        task_id=task.id,
        task_title=task.title,
        status=session.status,
        interaction_count=session.interaction_count,
        max_interactions=session.max_interactions,
        remaining_count=remaining_count,
        can_send=session.interaction_count < session.max_interactions and session.status != 'running',
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _session_to_detail_out(session: AgentSession, task: Task, remaining_count: int) -> AgentSessionDetailOut:
    return AgentSessionDetailOut(
        session_id=session.id,
        task_id=task.id,
        task_title=task.title,
        status=session.status,
        interaction_count=session.interaction_count,
        max_interactions=session.max_interactions,
        remaining_count=remaining_count,
        can_send=session.interaction_count < session.max_interactions and session.status != 'running',
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

    category = db.get(TaskCategory, task.category_id) if task.category_id else None
    if not category or not category.ai_agent_enabled:
        raise HTTPException(status_code=400, detail='该任务类别未开启 AI 代理')

    if task.assignee_id and task.assignee_id != user.id:
        raise HTTPException(status_code=400, detail='任务已有接单者，无法开启 AI 代理')

    if task.agent_session_id:
        existing = db.get(AgentSession, task.agent_session_id)
        if existing and existing.user_id == user.id and existing.interaction_count < existing.max_interactions:
            if task.status == TaskStatus.OPEN:
                task.status = TaskStatus.IN_PROGRESS
                db.add(task)
                db.commit()
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
    session = _get_owned_session(db, user.id, session_id)
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

    session = _get_owned_session(db, user.id, session_id)
    if session.status == 'running':
        raise HTTPException(status_code=409, detail='代理正在处理中，请稍后再发送')
    if session.interaction_count >= session.max_interactions:
        raise HTTPException(status_code=400, detail='当前代理会话交互次数已达上限，请重新开启代理')
    if is_agent_busy():
        raise HTTPException(status_code=409, detail='当前系统仅支持单代理运行，请稍后重试')

    text = content.strip()
    if not text and not files:
        raise HTTPException(status_code=422, detail='请输入需求描述或上传文件')
    if len(files) > MAX_AGENT_FILES_PER_MESSAGE:
        raise HTTPException(status_code=400, detail=f'单次最多上传 {MAX_AGENT_FILES_PER_MESSAGE} 个文件')

    ensure_session_workspace(user.id, session.id)
    target_dir = uploads_dir(user.id, session.id)
    target_dir.mkdir(parents=True, exist_ok=True)

    attachment_items: list[dict] = []
    for upload in files:
        raw = await upload.read(MAX_AGENT_FILE_SIZE + 1)
        if len(raw) > MAX_AGENT_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f'文件「{upload.filename or "未命名文件"}」超过 50 MB 限制',
            )
        original = upload.filename or 'unnamed'
        stored = f'{uuid.uuid4().hex}_{safe_filename(original)}'
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
    session.last_activity_at = datetime.utcnow()
    db.add(session)
    db.commit()

    spawn_agent_run(
        session.id,
        user_prompt=text or '请先查看我上传的文件，然后继续完成任务。',
        attachments=attachment_items,
    )

    return AgentSendOut(
        queued=True,
        interaction_count=session.interaction_count,
        max_interactions=session.max_interactions,
    )


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
    if not user_ids:
        raise HTTPException(status_code=422, detail='用户列表不能为空')

    users = db.query(User).filter(User.id.in_(user_ids)).all()
    for user in users:
        user.agent_usage_remaining = int(user.agent_usage_remaining or 0) + payload.amount
        db.add(user)

    db.add(AdminActionLog(
        admin_identifier=admin.admin_account or 'admin',
        action='grant_agent_usage',
        target_type='user_batch',
        target_id=','.join(str(uid) for uid in user_ids[:100]),
        detail=f'count={len(users)}, amount={payload.amount}',
    ))
    db.commit()
    return AgentBatchGrantOut(updated_user_count=len(users))


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
