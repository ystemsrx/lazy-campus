from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.session import get_db
from app.models.enums import TaskStatus
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User
from app.schemas.notification import NotificationOut

router = APIRouter(prefix='/notifications', tags=['notifications'])


@router.get('', response_model=list[NotificationOut])
def list_notifications(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[NotificationOut]:
    db_rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read == False)  # noqa: E712
        .order_by(desc(Notification.created_at))
        .limit(50)
        .all()
    )
    result: list[NotificationOut] = [NotificationOut.model_validate(n) for n in db_rows]

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
    for task in expired_tasks:
        result.append(
            NotificationOut(
                id=-(task.id),
                type='task_expired',
                title='任务已过期',
                description=f'「{task.title}」的截止时间已过，请及时处理',
                related_task_id=task.id,
                dismiss_type='action',
                is_read=False,
                created_at=task.deadline,
            )
        )

    result.sort(key=lambda x: x.created_at, reverse=True)
    return result


@router.get('/count')
def get_unread_count(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    db_count = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
        .scalar()
        or 0
    )

    now = datetime.utcnow()
    expired_count = (
        db.query(func.count(Task.id))
        .filter(
            Task.publisher_id == user.id,
            Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_PROGRESS]),
            Task.deadline.isnot(None),
            Task.deadline < now,
        )
        .scalar()
        or 0
    )

    return {'count': db_count + expired_count}


@router.post('/{notification_id}/read')
def mark_as_read(
    notification_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail='Notification not found')
    if notification.dismiss_type not in ('read',):
        raise HTTPException(status_code=400, detail='This notification cannot be dismissed by reading')
    db.delete(notification)
    db.commit()
    return {'message': 'ok'}


@router.post('/read-all')
def mark_all_as_read(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.dismiss_type == 'read',
    ).delete()
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
        raise HTTPException(status_code=400, detail='此通知在处罚解除前不可删除')
    db.delete(notification)
    db.commit()
    return {'message': 'ok'}
