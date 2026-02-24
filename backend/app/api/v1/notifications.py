from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.session import get_db
from app.models.enums import TaskStatus
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User
from app.schemas.notification import NotificationOut

router = APIRouter(prefix='/notifications', tags=['notifications'])


def _sync_task_expired_notifications(user: User, db: Session) -> None:
    """Ensure task_expired notifications exist as real DB records
    and clean up stale ones for tasks no longer expired."""
    now = datetime.utcnow()
    expired_tasks = (
        db.query(Task)
        .filter(
            Task.publisher_id == user.id,
            Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_PROGRESS]),
            Task.deadline.isnot(None),
            Task.deadline < now,
        )
        .all()
    )
    expired_task_ids = {t.id for t in expired_tasks}

    existing_rows = (
        db.query(Notification.related_task_id)
        .filter(
            Notification.user_id == user.id,
            Notification.type == 'task_expired',
        )
        .all()
    )
    existing_ids = {r[0] for r in existing_rows if r[0] is not None}

    changed = False

    for task in expired_tasks:
        if task.id not in existing_ids:
            db.add(Notification(
                user_id=user.id,
                type='task_expired',
                title='任务已过期',
                description=f'「{task.title}」的截止时间已过，请及时处理',
                related_task_id=task.id,
                dismiss_type='persistent',
                is_read=False,
                created_at=task.deadline or now,
            ))
            changed = True

    stale_ids = existing_ids - expired_task_ids
    if stale_ids:
        db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.type == 'task_expired',
            Notification.related_task_id.in_(stale_ids),
        ).delete(synchronize_session=False)
        changed = True

    if changed:
        db.commit()


@router.get('', response_model=list[NotificationOut])
def list_notifications(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[NotificationOut]:
    _sync_task_expired_notifications(user, db)

    db_rows = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            or_(Notification.is_read == False, Notification.dismiss_type == 'persistent'),  # noqa: E712
        )
        .order_by(desc(Notification.created_at))
        .limit(50)
        .all()
    )
    return [NotificationOut.model_validate(n) for n in db_rows]


@router.get('/count')
def get_unread_count(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    _sync_task_expired_notifications(user, db)

    db_count = (
        db.query(func.count(Notification.id))
        .filter(
            Notification.user_id == user.id,
            or_(Notification.is_read.is_(False), Notification.dismiss_type == 'persistent'),
        )
        .scalar()
        or 0
    )
    return {'count': db_count}


@router.post('/{notification_id}/read')
def mark_as_read(
    notification_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail='Notification not found')
    notification.is_read = True
    db.commit()
    return {'message': 'ok'}


@router.post('/read-all')
def mark_all_as_read(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False,  # noqa: E712
    ).update({'is_read': True})
    db.commit()
    return {'message': 'ok'}


@router.post('/dismiss-chat/{task_id}')
def dismiss_chat_notification(
    task_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.type == 'chat_message',
        Notification.related_task_id == task_id,
    ).delete()
    db.commit()
    return {'message': 'ok'}


@router.delete('/{notification_id}')
def delete_notification(
    notification_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail='Notification not found')
    if notification.dismiss_type == 'persistent':
        raise HTTPException(status_code=400, detail='此通知无法手动删除')
    db.delete(notification)
    db.commit()
    return {'message': 'ok'}
