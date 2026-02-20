import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, asc, case, desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps import optional_user, require_admin, require_completed_user, require_user
from app.db.session import get_db
from app.models.enums import ContactVisibility, RatingTargetRole, TaskStatus
from app.models.moderation import Blacklist
from app.models.task import Task, TaskAttachment, TaskCategory, TaskMessage, TaskReview
from app.models.user import User
from app.schemas.task import (
    TaskAttachmentCreate,
    TaskAttachmentOut,
    CategoryCreate,
    CategoryOut,
    TaskCreate,
    TaskMessageCreate,
    TaskMessageOut,
    TaskOut,
    TaskReviewCreate,
    TaskReviewOut,
    TaskUpdate,
)
from app.utils.user_display import display_name

router = APIRouter(prefix='/tasks', tags=['tasks'])

_BAYESIAN_C = 3
_DECAY_LAMBDA = math.log(2) / 48.0  # 2-day half-life
_URGENCY_CAP = 0.1
_URGENCY_WINDOW_H = 72.0
_BLOCK_K = 0.5
_BAN_K = 1.5


def _publisher_mu(db: Session) -> float:
    val = db.query(func.avg(User.publisher_rating_avg)).filter(User.publisher_rating_count > 0).scalar()
    return float(val) if val else 3.0


def _task_ranking_score(task: Task, publisher: User, now: datetime, mu: float, completed: int) -> float:
    """Credibility × Freshness × (1 + Urgency) − Penalty"""
    ce = math.sqrt(completed)
    ra = publisher.publisher_rating_avg if publisher.publisher_rating_count > 0 else mu
    bayesian = (_BAYESIAN_C * mu + ra * ce) / (_BAYESIAN_C + ce)

    age_h = max(0.0, (now - task.created_at).total_seconds() / 3600)
    freshness = math.exp(-_DECAY_LAMBDA * age_h)

    urgency = 0.0
    if task.deadline and task.deadline > now:
        left_h = (task.deadline - now).total_seconds() / 3600
        urgency = min(_URGENCY_CAP, _URGENCY_CAP / (1.0 + left_h / _URGENCY_WINDOW_H))

    penalty = math.log1p(publisher.blocked_by_count) * _BLOCK_K + math.log1p(publisher.ban_count or 0) * _BAN_K
    return bayesian * freshness * (1.0 + urgency) - penalty


def _is_participant(task: Task, user_id: int) -> bool:
    return task.publisher_id == user_id or task.assignee_id == user_id


def _contact_visible(task: Task, user_id: int | None) -> bool:
    if not user_id:
        return False
    if task.publisher_id == user_id:
        return True
    if task.contact_visibility == ContactVisibility.INTERNAL_ONLY:
        return False
    return task.assignee_id == user_id


def _task_to_out(task: Task, publisher: User, assignee: User | None, viewer_id: int | None = None) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        deadline=task.deadline,
        location=task.location,
        price=task.price,
        status=task.status,
        category_id=task.category_id,
        publisher_id=task.publisher_id,
        assignee_id=task.assignee_id,
        contact_visibility=task.contact_visibility,
        contact_info=task.contact_info if _contact_visible(task, viewer_id) else None,
        required_gender=task.required_gender,
        publisher_display_name=display_name(publisher),
        assignee_display_name=display_name(assignee) if assignee else None,
        created_at=task.created_at,
    )


def _blocked_between(db: Session, user_a: int, user_b: int) -> bool:
    blocked = (
        db.query(Blacklist)
        .filter(
            or_(
                and_(Blacklist.user_id == user_a, Blacklist.blocked_user_id == user_b),
                and_(Blacklist.user_id == user_b, Blacklist.blocked_user_id == user_a),
            )
        )
        .first()
    )
    return blocked is not None


def _update_user_rating(db: Session, reviewee_id: int, target_role: RatingTargetRole) -> None:
    rows = (
        db.query(TaskReview.stars)
        .filter(TaskReview.reviewee_id == reviewee_id, TaskReview.target_role == target_role)
        .all()
    )
    count = len(rows)
    avg = (sum(row[0] for row in rows) / count) if count else 0

    user = db.get(User, reviewee_id)
    if not user:
        return

    if target_role == RatingTargetRole.PUBLISHER:
        user.publisher_rating_count = count
        user.publisher_rating_avg = round(avg, 2)
    else:
        user.worker_rating_count = count
        user.worker_rating_avg = round(avg, 2)
    db.add(user)
    db.commit()


@router.get('/categories', response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    return db.query(TaskCategory).order_by(asc(TaskCategory.sort_order), asc(TaskCategory.id)).all()


@router.post('/categories', response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
) -> CategoryOut:
    existing = db.query(TaskCategory).filter(TaskCategory.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail='Category already exists')
    category = TaskCategory(name=payload.name, description=payload.description, sort_order=payload.sort_order)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put('/categories/{category_id}', response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
) -> CategoryOut:
    category = db.get(TaskCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail='Category not found')

    duplicate = (
        db.query(TaskCategory)
        .filter(TaskCategory.name == payload.name, TaskCategory.id != category_id)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail='Category name already exists')

    category.name = payload.name
    category.description = payload.description
    category.sort_order = payload.sort_order
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete('/categories/{category_id}')
def delete_category(
    category_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    category = db.get(TaskCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail='Category not found')
    db.delete(category)
    db.commit()
    return {'message': 'deleted'}


@router.get('', response_model=list[TaskOut])
def list_tasks(
    keyword: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    status: TaskStatus | None = Query(default=TaskStatus.OPEN),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    sort: str = Query(
        default='ranking',
        pattern='^(ranking|newest|deadline_asc|publisher_rating|publisher_completed|price_asc|price_desc)$',
    ),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    query = db.query(Task, User).join(User, Task.publisher_id == User.id).filter(User.is_banned.is_(False))

    if keyword:
        like = f'%{keyword}%'
        query = query.filter(or_(Task.title.like(like), Task.description.like(like), Task.location.like(like)))
    if category_id is not None:
        query = query.filter(Task.category_id == category_id)
    if status is not None:
        query = query.filter(Task.status == status)
        if status == TaskStatus.OPEN:
            now_filter = datetime.utcnow()
            query = query.filter(or_(Task.deadline.is_(None), Task.deadline > now_filter))
    if min_price is not None:
        query = query.filter(Task.price >= min_price)
    if max_price is not None:
        query = query.filter(Task.price <= max_price)

    if sort == 'newest':
        query = query.order_by(desc(Task.created_at))
        rows = query.limit(200).all()
    elif sort == 'deadline_asc':
        query = query.order_by(
            case((Task.deadline.is_(None), 1), else_=0),
            asc(Task.deadline),
            desc(Task.created_at),
        )
        rows = query.limit(200).all()
    elif sort == 'publisher_rating':
        query = query.order_by(desc(User.publisher_rating_avg), desc(User.publisher_rating_count), desc(Task.created_at))
        rows = query.limit(200).all()
    elif sort == 'publisher_completed':
        rows = query.all()
        pub_ids = {p.id for _, p in rows}
        completed_map: dict[int, int] = {}
        if pub_ids:
            completed_map = dict(
                db.query(Task.publisher_id, func.count(Task.id))
                .filter(Task.publisher_id.in_(pub_ids), Task.status == TaskStatus.COMPLETED)
                .group_by(Task.publisher_id)
                .all()
            )
        rows.sort(key=lambda r: (-completed_map.get(r[1].id, 0), -r[0].created_at.timestamp()))
        rows = rows[:200]
    elif sort == 'price_asc':
        query = query.order_by(asc(Task.price), desc(Task.created_at))
        rows = query.limit(200).all()
    elif sort == 'price_desc':
        query = query.order_by(desc(Task.price), desc(Task.created_at))
        rows = query.limit(200).all()
    else:
        rows = query.all()
        now = datetime.utcnow()
        mu = _publisher_mu(db)
        pub_ids = {p.id for _, p in rows}
        cmap: dict[int, int] = {}
        if pub_ids:
            cmap = dict(
                db.query(Task.publisher_id, func.count(Task.id))
                .filter(Task.publisher_id.in_(pub_ids), Task.status == TaskStatus.COMPLETED)
                .group_by(Task.publisher_id)
                .all()
            )
        user_gender = user.gender
        def _rank_key(r):
            task, pub = r
            mismatch = 1 if (task.required_gender and task.required_gender != user_gender) else 0
            return (mismatch, -_task_ranking_score(task, pub, now, mu, cmap.get(pub.id, 0)))
        rows.sort(key=_rank_key)
        rows = rows[:200]

    user_ids = {task.assignee_id for task, _ in rows if task.assignee_id}
    assignees = {}
    if user_ids:
        assignees = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    return [_task_to_out(task, publisher, assignees.get(task.assignee_id), user.id) for task, publisher in rows]


@router.post('', response_model=TaskOut)
def create_task(
    payload: TaskCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    if payload.contact_visibility == ContactVisibility.AFTER_ACCEPT and not payload.contact_info:
        raise HTTPException(status_code=422, detail='contact_info is required when contact visibility is after_accept')
    if payload.contact_visibility == ContactVisibility.INTERNAL_ONLY and payload.contact_info:
        raise HTTPException(status_code=422, detail='contact_info should be empty for internal_only mode')

    if payload.deadline and payload.deadline <= datetime.utcnow():
        raise HTTPException(status_code=422, detail='截止时间不能早于当前时间')

    task = Task(
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        location=payload.location,
        price=payload.price,
        category_id=payload.category_id,
        contact_visibility=payload.contact_visibility,
        contact_info=payload.contact_info,
        required_gender=payload.required_gender,
        publisher_id=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return _task_to_out(task, user, assignee=None, viewer_id=user.id)


@router.get('/{task_id}', response_model=TaskOut)
def get_task(task_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)) -> TaskOut:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    publisher = db.get(User, task.publisher_id)
    assignee = db.get(User, task.assignee_id) if task.assignee_id else None
    return _task_to_out(task, publisher, assignee, viewer_id=user.id)


@router.put('/{task_id}', response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if task.publisher_id != user.id:
        raise HTTPException(status_code=403, detail='Only publisher can update task')
    if task.status != TaskStatus.OPEN:
        raise HTTPException(status_code=400, detail='Task already accepted or closed')

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(task, k, v)

    if task.deadline and task.deadline <= datetime.utcnow():
        raise HTTPException(status_code=422, detail='截止时间不能早于当前时间')

    if task.contact_visibility == ContactVisibility.AFTER_ACCEPT and not task.contact_info:
        raise HTTPException(status_code=422, detail='contact_info is required when contact visibility is after_accept')
    if task.contact_visibility == ContactVisibility.INTERNAL_ONLY:
        task.contact_info = None

    db.add(task)
    db.commit()
    db.refresh(task)

    return _task_to_out(task, user, None, viewer_id=user.id)


@router.post('/{task_id}/accept', response_model=TaskOut)
def accept_task(task_id: int, user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> TaskOut:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if task.publisher_id == user.id:
        raise HTTPException(status_code=400, detail='Cannot accept your own task')
    if task.status != TaskStatus.OPEN:
        raise HTTPException(status_code=400, detail='Task is not open')
    if _blocked_between(db, user.id, task.publisher_id):
        raise HTTPException(status_code=403, detail='Blocked relation detected')
    if task.required_gender and user.gender != task.required_gender:
        raise HTTPException(status_code=400, detail='您的性别不满足该任务要求')

    task.assignee_id = user.id
    task.status = TaskStatus.IN_PROGRESS
    db.add(task)
    db.commit()
    db.refresh(task)

    publisher = db.get(User, task.publisher_id)
    return _task_to_out(task, publisher, user, viewer_id=user.id)


@router.post('/{task_id}/confirm-complete', response_model=TaskOut)
def confirm_complete(task_id: int, user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> TaskOut:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if task.publisher_id != user.id:
        raise HTTPException(status_code=403, detail='Only publisher can confirm completion')
    if task.status != TaskStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail='Task not in progress')

    task.status = TaskStatus.COMPLETED
    db.add(task)
    db.commit()
    db.refresh(task)

    assignee = db.get(User, task.assignee_id) if task.assignee_id else None
    return _task_to_out(task, user, assignee, viewer_id=user.id)


@router.post('/{task_id}/cancel', response_model=TaskOut)
def cancel_task(task_id: int, user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> TaskOut:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if not _is_participant(task, user.id):
        raise HTTPException(status_code=403, detail='Not allowed')
    if task.status == TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail='Completed task cannot be canceled')

    task.status = TaskStatus.CANCELED
    db.add(task)
    db.commit()
    db.refresh(task)

    publisher = db.get(User, task.publisher_id)
    assignee = db.get(User, task.assignee_id) if task.assignee_id else None
    return _task_to_out(task, publisher, assignee, viewer_id=user.id)


@router.delete('/{task_id}')
def delete_task(task_id: int, user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if task.publisher_id != user.id:
        raise HTTPException(status_code=403, detail='Only publisher can delete task')
    if task.status == TaskStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail='任务已被接取，请等待接单者取消后再删除')
    if task.status not in (TaskStatus.OPEN, TaskStatus.CANCELED):
        raise HTTPException(status_code=400, detail='当前任务状态不允许删除')

    db.query(TaskMessage).filter(TaskMessage.task_id == task_id).delete()
    db.query(TaskAttachment).filter(TaskAttachment.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    return {'message': 'deleted'}


@router.get('/{task_id}/messages', response_model=list[TaskMessageOut])
def list_messages(task_id: int, user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> list[TaskMessageOut]:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if not _is_participant(task, user.id):
        raise HTTPException(status_code=403, detail='Only participants can read messages')

    rows = db.query(TaskMessage).filter(TaskMessage.task_id == task_id).order_by(asc(TaskMessage.created_at)).limit(500).all()
    sender_ids = {row.sender_id for row in rows}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(sender_ids)).all()} if sender_ids else {}

    return [
        TaskMessageOut(
            id=row.id,
            task_id=row.task_id,
            sender_id=row.sender_id,
            sender_display_name=display_name(users.get(row.sender_id)) if users.get(row.sender_id) else '未知用户',
            content=row.content,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post('/{task_id}/messages', response_model=TaskMessageOut)
def send_message(
    task_id: int,
    payload: TaskMessageCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> TaskMessageOut:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if not _is_participant(task, user.id):
        raise HTTPException(status_code=403, detail='Only participants can chat')

    other_id = task.assignee_id if user.id == task.publisher_id else task.publisher_id
    if other_id and _blocked_between(db, user.id, other_id):
        raise HTTPException(status_code=403, detail='Blocked relation detected')

    last_message = (
        db.query(TaskMessage)
        .filter(TaskMessage.task_id == task_id, TaskMessage.sender_id == user.id)
        .order_by(desc(TaskMessage.created_at))
        .first()
    )
    if last_message and datetime.utcnow() - last_message.created_at < timedelta(seconds=3):
        raise HTTPException(status_code=429, detail='Message sending too frequently')

    message = TaskMessage(task_id=task_id, sender_id=user.id, content=payload.content)
    db.add(message)
    db.commit()
    db.refresh(message)

    return TaskMessageOut(
        id=message.id,
        task_id=task_id,
        sender_id=user.id,
        sender_display_name=display_name(user),
        content=message.content,
        created_at=message.created_at,
    )


@router.get('/{task_id}/attachments', response_model=list[TaskAttachmentOut])
def list_attachments(
    task_id: int,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> list[TaskAttachmentOut]:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if not _is_participant(task, user.id):
        raise HTTPException(status_code=403, detail='Only participants can access attachments')
    return db.query(TaskAttachment).filter(TaskAttachment.task_id == task_id).order_by(asc(TaskAttachment.created_at)).all()


@router.post('/{task_id}/attachments', response_model=TaskAttachmentOut)
def create_attachment(
    task_id: int,
    payload: TaskAttachmentCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> TaskAttachmentOut:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if not _is_participant(task, user.id):
        raise HTTPException(status_code=403, detail='Only participants can upload attachments')

    attachment = TaskAttachment(
        task_id=task_id,
        uploader_id=user.id,
        file_name=payload.file_name,
        file_url=payload.file_url,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get('/{task_id}/reviews', response_model=list[TaskReviewOut])
def list_reviews(
    task_id: int,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> list[TaskReviewOut]:
    reviews = db.query(TaskReview).filter(TaskReview.task_id == task_id).order_by(desc(TaskReview.created_at)).all()

    if not user:
        return reviews

    task = db.get(Task, task_id)
    if not task or not _is_participant(task, user.id):
        return reviews

    roles_reviewed = {r.target_role for r in reviews}
    both_done = RatingTargetRole.PUBLISHER in roles_reviewed and RatingTargetRole.WORKER in roles_reviewed
    if both_done:
        return reviews

    return [r for r in reviews if r.reviewer_id == user.id]


@router.post('/{task_id}/reviews', response_model=TaskReviewOut)
def create_review(
    task_id: int,
    payload: TaskReviewCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> TaskReviewOut:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail='Task is not completed')
    if not _is_participant(task, user.id):
        raise HTTPException(status_code=403, detail='Only participants can review')

    if payload.target_role == RatingTargetRole.PUBLISHER:
        reviewee_id = task.publisher_id
        if user.id != task.assignee_id:
            raise HTTPException(status_code=400, detail='Only assignee can rate publisher')
    else:
        reviewee_id = task.assignee_id
        if not reviewee_id:
            raise HTTPException(status_code=400, detail='Task has no assignee')
        if user.id != task.publisher_id:
            raise HTTPException(status_code=400, detail='Only publisher can rate assignee')

    existing = (
        db.query(TaskReview)
        .filter(TaskReview.task_id == task_id, TaskReview.reviewer_id == user.id, TaskReview.target_role == payload.target_role)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail='You already reviewed this role for the task')

    review = TaskReview(
        task_id=task_id,
        reviewer_id=user.id,
        reviewee_id=reviewee_id,
        target_role=payload.target_role,
        stars=payload.stars,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    _update_user_rating(db, reviewee_id, payload.target_role)

    return review


@router.get('/me/published', response_model=list[TaskOut])
def list_my_published(user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> list[TaskOut]:
    rows = db.query(Task).filter(Task.publisher_id == user.id).order_by(desc(Task.created_at)).limit(200).all()
    assignee_ids = {r.assignee_id for r in rows if r.assignee_id}
    assignees = {u.id: u for u in db.query(User).filter(User.id.in_(assignee_ids)).all()} if assignee_ids else {}
    return [_task_to_out(task, user, assignees.get(task.assignee_id), viewer_id=user.id) for task in rows]


@router.get('/me/accepted', response_model=list[TaskOut])
def list_my_accepted(user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> list[TaskOut]:
    rows = db.query(Task).filter(Task.assignee_id == user.id).order_by(desc(Task.created_at)).limit(200).all()
    publisher_ids = {r.publisher_id for r in rows}
    publishers = {u.id: u for u in db.query(User).filter(User.id.in_(publisher_ids)).all()} if publisher_ids else {}
    return [_task_to_out(task, publishers.get(task.publisher_id), user, viewer_id=user.id) for task in rows]
