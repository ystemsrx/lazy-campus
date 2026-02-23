import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.api.deps import require_completed_user
from app.core.config import settings
from app.db.session import get_db
from app.models.chat import ChatAttachment, ChatMessage
from app.models.moderation import Blacklist
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User
from app.schemas.chat import (
    AttachmentCountOut,
    ChatAttachmentOut,
    ChatMessageOut,
    ChatMessageSend,
    ConversationOut,
)
from app.utils.user_display import display_name
from app.services.captcha_service import (
    captcha_required,
    clear_gate_required,
    consume_captcha_token,
    is_gate_required,
    set_gate_required,
)

router = APIRouter(prefix='/chat', tags=['chat'])

UPLOADS_ROOT = Path(__file__).resolve().parents[3] / 'uploads'
CHAT_UPLOADS_ROOT = UPLOADS_ROOT / 'chat'
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ATTACHMENTS_PER_CONVERSATION = 5
CHAT_CAPTCHA_SCENE = 'chat_send'
CHAT_CAPTCHA_WINDOW_SECONDS = 60
CHAT_CAPTCHA_THRESHOLD = 8


def _conversation_key(user_id: int, peer_id: int) -> tuple[int, int]:
    return (min(user_id, peer_id), max(user_id, peer_id))


def _is_blocked(db: Session, user_id: int, peer_id: int) -> tuple[bool, bool]:
    blocked_by_me = db.query(Blacklist).filter(
        Blacklist.user_id == user_id, Blacklist.blocked_user_id == peer_id
    ).first() is not None
    blocked_by_them = db.query(Blacklist).filter(
        Blacklist.user_id == peer_id, Blacklist.blocked_user_id == user_id
    ).first() is not None
    return blocked_by_me, blocked_by_them


def _sent_message_count_in_window(db: Session, sender_id: int, seconds: int) -> int:
    window_start = datetime.utcnow() - timedelta(seconds=seconds)
    return (
        db.query(func.count(ChatMessage.id))
        .filter(ChatMessage.sender_id == sender_id, ChatMessage.created_at >= window_start)
        .scalar()
        or 0
    )


@router.get('/conversations', response_model=list[ConversationOut])
def list_conversations(
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> list[ConversationOut]:
    uid = user.id

    is_sender = ChatMessage.sender_id == uid
    peer_id_expr = case((is_sender, ChatMessage.receiver_id), else_=ChatMessage.sender_id)

    subq = (
        db.query(
            peer_id_expr.label('peer_id'),
            ChatMessage.task_id.label('task_id'),
            func.max(ChatMessage.created_at).label('last_time'),
            func.sum(
                case(
                    (and_(ChatMessage.receiver_id == uid, ChatMessage.is_read == False, ChatMessage.blocked == False), 1),  # noqa: E712
                    else_=0,
                )
            ).label('unread'),
        )
        .filter(
            or_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == uid),
            or_(ChatMessage.blocked.is_(False), ChatMessage.sender_id == uid),
        )
        .group_by(peer_id_expr, ChatMessage.task_id)
        .subquery()
    )

    rows = db.query(subq).all()

    blocked_by_me_ids = {
        b.blocked_user_id
        for b in db.query(Blacklist).filter(Blacklist.user_id == uid).all()
    }
    blocked_me_ids = {
        b.user_id
        for b in db.query(Blacklist).filter(Blacklist.blocked_user_id == uid).all()
    }

    results: list[ConversationOut] = []
    for row in rows:
        peer = db.get(User, row.peer_id)
        if not peer:
            continue

        task = db.get(Task, row.task_id) if row.task_id else None

        last_msg = (
            db.query(ChatMessage)
            .filter(
                or_(
                    and_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == row.peer_id),
                    and_(ChatMessage.sender_id == row.peer_id, ChatMessage.receiver_id == uid),
                ),
                ChatMessage.task_id == row.task_id if row.task_id else ChatMessage.task_id.is_(None),
                or_(ChatMessage.blocked.is_(False), ChatMessage.sender_id == uid),
            )
            .order_by(ChatMessage.created_at.desc())
            .first()
        )

        results.append(
            ConversationOut(
                peer_id=row.peer_id,
                peer_name=display_name(peer),
                peer_avatar=peer.avatar_url,
                peer_gender=peer.gender.value if peer.gender else None,
                peer_last_active=peer.last_active,
                task_id=row.task_id,
                task_title=task.title if task else None,
                task_price=task.price if task else None,
                task_status=task.status.value if task else None,
                task_icon=task.icon if task else None,
                task_is_deleted=bool(task.is_deleted) if task else False,
                last_message=last_msg.content[:100] if last_msg else None,
                last_message_time=last_msg.created_at if last_msg else None,
                unread_count=int(row.unread or 0),
                blocked_by_me=row.peer_id in blocked_by_me_ids,
                blocked_by_them=row.peer_id in blocked_me_ids,
                peer_ban_contact=bool(peer.ban_contact),
            )
        )

    normal = [c for c in results if not c.blocked_by_me and not c.blocked_by_them]
    blocked = [c for c in results if c.blocked_by_me or c.blocked_by_them]
    normal.sort(key=lambda c: c.last_message_time or datetime.min, reverse=True)
    blocked.sort(key=lambda c: c.last_message_time or datetime.min, reverse=True)
    return normal + blocked


@router.get('/messages', response_model=list[ChatMessageOut])
def get_messages(
    peer_id: int,
    task_id: int | None = None,
    before: int | None = None,
    limit: int = Query(default=50, le=100),
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> list[ChatMessageOut]:
    uid = user.id
    task_filter = ChatMessage.task_id == task_id if task_id else ChatMessage.task_id.is_(None)

    q = db.query(ChatMessage).filter(
        or_(
            and_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == peer_id),
            and_(ChatMessage.sender_id == peer_id, ChatMessage.receiver_id == uid),
        ),
        task_filter,
        or_(
            ChatMessage.blocked.is_(False),
            ChatMessage.sender_id == uid,
        ),
    )

    if before:
        q = q.filter(ChatMessage.id < before)

    msgs = q.order_by(ChatMessage.created_at.desc()).limit(limit).all()
    msgs.reverse()
    return msgs


@router.get('/messages/snapshot', response_model=list[ChatMessageOut])
def get_message_snapshot(
    peer_id: int,
    task_id: int | None = None,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> list[ChatMessageOut]:
    """任务详情中的聊天快照，仅返回最近 10 条。"""
    uid = user.id
    task_filter = ChatMessage.task_id == task_id if task_id else ChatMessage.task_id.is_(None)

    msgs = (
        db.query(ChatMessage)
        .filter(
            or_(
                and_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == peer_id),
                and_(ChatMessage.sender_id == peer_id, ChatMessage.receiver_id == uid),
            ),
            task_filter,
            or_(
                ChatMessage.blocked.is_(False),
                ChatMessage.sender_id == uid,
            ),
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )
    msgs.reverse()
    return msgs


@router.post('/messages', response_model=ChatMessageOut)
def send_message(
    peer_id: int,
    body: ChatMessageSend,
    task_id: int | None = None,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> ChatMessageOut:
    uid = user.id
    if uid == peer_id:
        raise HTTPException(status_code=400, detail='不能给自己发消息')
    if user.ban_contact:
        raise HTTPException(status_code=403, detail='你的账号已被禁止联系他人')

    peer = db.get(User, peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail='用户不存在')

    peer_banned = bool(peer.ban_contact)

    blocked_by_me, blocked_by_them = _is_blocked(db, uid, peer_id)
    if blocked_by_me or blocked_by_them:
        raise HTTPException(status_code=403, detail='已拉黑，无法发送消息')

    if is_gate_required(db, uid, CHAT_CAPTCHA_SCENE):
        valid = consume_captcha_token(
            db=db,
            user_id=uid,
            scene=CHAT_CAPTCHA_SCENE,
            token=body.captcha_token.strip() if body.captcha_token else None,
        )
        if not valid:
            captcha_required(
                scene=CHAT_CAPTCHA_SCENE,
                message='发送频率过高，请先完成滑块验证后继续聊天',
            )
        clear_gate_required(db, uid, CHAT_CAPTCHA_SCENE)
    elif _sent_message_count_in_window(db, uid, CHAT_CAPTCHA_WINDOW_SECONDS) >= CHAT_CAPTCHA_THRESHOLD:
        set_gate_required(db, uid, CHAT_CAPTCHA_SCENE)
        captcha_required(
            scene=CHAT_CAPTCHA_SCENE,
            message='发送频率过高，请先完成滑块验证后继续聊天',
        )

    if task_id:
        task = db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail='任务不存在')

    if not body.content.strip():
        raise HTTPException(status_code=400, detail='消息不能为空')

    msg = ChatMessage(
        sender_id=uid,
        receiver_id=peer_id,
        task_id=task_id,
        content=body.content.strip(),
        blocked=peer_banned,
    )
    db.add(msg)

    if not peer_banned:
        task_obj = db.get(Task, task_id) if task_id else None
        desc = f'在「{task_obj.title}」中有新消息' if task_obj else '有新消息'

        existing_notif = db.query(Notification).filter(
            Notification.user_id == peer_id,
            Notification.type == 'chat_message',
            Notification.related_user_id == uid,
            Notification.related_task_id == task_id if task_id else Notification.related_task_id.is_(None),
        ).first()

        if existing_notif:
            existing_notif.title = display_name(user)
            existing_notif.description = desc
            existing_notif.is_read = False
            existing_notif.updated_at = datetime.now(timezone.utc)
            db.add(existing_notif)
        else:
            db.add(Notification(
                user_id=peer_id,
                type='chat_message',
                title=display_name(user),
                description=desc,
                related_task_id=task_id,
                related_user_id=uid,
                dismiss_type='source',
            ))

    db.commit()
    db.refresh(msg)
    return msg


@router.post('/messages/read')
def mark_read(
    peer_id: int,
    task_id: int | None = None,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> dict:
    uid = user.id
    task_filter = ChatMessage.task_id == task_id if task_id else ChatMessage.task_id.is_(None)

    count = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.sender_id == peer_id,
            ChatMessage.receiver_id == uid,
            ChatMessage.is_read == False,  # noqa: E712
            task_filter,
        )
        .update({ChatMessage.is_read: True})
    )

    notif_filter = (
        Notification.related_task_id == task_id
        if task_id
        else Notification.related_task_id.is_(None)
    )
    db.query(Notification).filter(
        Notification.user_id == uid,
        Notification.type == 'chat_message',
        Notification.related_user_id == peer_id,
        notif_filter,
    ).delete()

    db.commit()
    return {'marked': count}


# ── 附件管理 ──────────────────────────────────────────────────────────────

@router.get('/attachments', response_model=list[ChatAttachmentOut])
def list_attachments(
    peer_id: int,
    task_id: int | None = None,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> list[ChatAttachmentOut]:
    uid = user.id
    task_filter = ChatAttachment.task_id == task_id if task_id else ChatAttachment.task_id.is_(None)
    lo, hi = _conversation_key(uid, peer_id)

    return (
        db.query(ChatAttachment)
        .filter(
            or_(
                and_(ChatAttachment.uploader_id == lo, ChatAttachment.peer_id == hi),
                and_(ChatAttachment.uploader_id == hi, ChatAttachment.peer_id == lo),
            ),
            task_filter,
        )
        .order_by(ChatAttachment.created_at.desc())
        .all()
    )


@router.get('/attachments/count', response_model=AttachmentCountOut)
def attachment_count(
    peer_id: int,
    task_id: int | None = None,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> AttachmentCountOut:
    uid = user.id
    task_filter = ChatAttachment.task_id == task_id if task_id else ChatAttachment.task_id.is_(None)
    lo, hi = _conversation_key(uid, peer_id)

    count = (
        db.query(func.count(ChatAttachment.id))
        .filter(
            or_(
                and_(ChatAttachment.uploader_id == lo, ChatAttachment.peer_id == hi),
                and_(ChatAttachment.uploader_id == hi, ChatAttachment.peer_id == lo),
            ),
            task_filter,
        )
        .scalar()
    )
    return AttachmentCountOut(count=count or 0, limit=MAX_ATTACHMENTS_PER_CONVERSATION)


@router.post('/attachments', response_model=ChatAttachmentOut)
async def upload_attachment(
    peer_id: int,
    file: UploadFile,
    task_id: int | None = None,
    message_id: int | None = None,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> ChatAttachmentOut:
    uid = user.id
    if user.ban_contact:
        raise HTTPException(status_code=403, detail='你的账号已被禁止联系他人')

    blocked_by_me, blocked_by_them = _is_blocked(db, uid, peer_id)
    if blocked_by_me or blocked_by_them:
        raise HTTPException(status_code=403, detail='已拉黑，无法发送附件')

    task_filter = ChatAttachment.task_id == task_id if task_id else ChatAttachment.task_id.is_(None)
    lo, hi = _conversation_key(uid, peer_id)
    existing = (
        db.query(func.count(ChatAttachment.id))
        .filter(
            or_(
                and_(ChatAttachment.uploader_id == lo, ChatAttachment.peer_id == hi),
                and_(ChatAttachment.uploader_id == hi, ChatAttachment.peer_id == lo),
            ),
            task_filter,
        )
        .scalar()
        or 0
    )
    if existing >= MAX_ATTACHMENTS_PER_CONVERSATION:
        raise HTTPException(
            status_code=400,
            detail=f'每个会话最多上传 {MAX_ATTACHMENTS_PER_CONVERSATION} 个附件',
        )

    data = await file.read(MAX_ATTACHMENT_SIZE + 1)
    if len(data) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(status_code=413, detail='文件过大，单个附件不得超过 10 MB')

    now = datetime.now(timezone.utc)
    dest_dir = CHAT_UPLOADS_ROOT / str(now.year) / f'{now.month:02d}'
    dest_dir.mkdir(parents=True, exist_ok=True)

    original_name = file.filename or 'unnamed'
    ext = Path(original_name).suffix
    stored_name = f'{uuid.uuid4().hex}{ext}'
    (dest_dir / stored_name).write_bytes(data)

    file_url = f'{settings.backend_public_url}{settings.api_v1_prefix}/chat/files/{stored_name}'

    attachment = ChatAttachment(
        uploader_id=uid,
        peer_id=peer_id,
        task_id=task_id,
        message_id=message_id,
        file_name=original_name,
        file_url=file_url,
        file_size=len(data),
        mime_type=file.content_type or 'application/octet-stream',
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.delete('/attachments/{attachment_id}')
def delete_attachment(
    attachment_id: int,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> dict:
    att = db.get(ChatAttachment, attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail='附件不存在')
    if att.uploader_id != user.id:
        raise HTTPException(status_code=403, detail='只能删除自己上传的附件')

    stored_name = att.file_url.rsplit('/', 1)[-1]
    matches = list(CHAT_UPLOADS_ROOT.glob(f'**/{stored_name}'))
    for f in matches:
        f.unlink(missing_ok=True)

    db.delete(att)
    db.commit()
    return {'deleted': True}


@router.get('/files/{filename}')
async def serve_chat_file(filename: str, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    if '/' in filename or '\\' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail='非法文件名')

    matches = list(CHAT_UPLOADS_ROOT.glob(f'**/{filename}'))
    if not matches:
        raise HTTPException(status_code=404, detail='文件不存在')

    att = db.query(ChatAttachment).filter(
        ChatAttachment.file_url.contains(filename)
    ).first()
    original_name = att.file_name if att else filename

    import mimetypes
    target = matches[0]
    media_type = mimetypes.guess_type(original_name)[0] or 'application/octet-stream'
    return FileResponse(path=str(target), media_type=media_type, filename=original_name)
