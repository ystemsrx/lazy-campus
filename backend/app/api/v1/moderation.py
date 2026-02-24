import json
import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_admin, require_completed_user, require_user
from app.db.session import get_db
from app.models.enums import Gender, ReportStatus, ReportType, TaskStatus, UserRole
from app.models.chat import ChatAttachment, ChatMessage
from app.models.moderation import AdminActionLog, Blacklist, Report
from app.models.notification import Notification
from app.models.task import Task, TaskAbandonLog, TaskAcceptLog, TaskAttachment, TaskCancelLog, TaskCategory, TaskMessage, TaskPublishLog, TaskReview
from app.models.user import User, WorkerProfile, worker_skill_tags
from app.schemas.moderation import (
    AdminActionLogItem,
    AdminActionLogListResponse,
    AdminBlacklistItem,
    AdminChatAttachmentOut,
    AdminChatConversationItem,
    AdminChatConversationListResponse,
    AdminChatMessageOut,
    AdminMiniUser,
    AdminPushNotificationOut,
    AdminPushNotificationRequest,
    AdminSentNotificationItem,
    AdminSentNotificationListResponse,
    AdminRiskUser,
    AdminTaskItem,
    AdminTaskListResponse,
    AdminTaskChatConversationItem,
    AdminTaskChatConversationListResponse,
    AdminTaskChatMessageOut,
    AdminTaskOperateRequest,
    AdminTrendPoint,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserProfileOut,
    AdminUserRadarMetrics,
    AdminUserReportBrief,
    AdminUserTaskBrief,
    AdminUserUpdateRequest,
    AppealCreate,
    AuthenticatedAppealCreate,
    BanContextOut,
    BanContextRequest,
    BanRecord,
    BanUserRequest,
    BlacklistCreate,
    DirectChatHistoryOut,
    DirectChatMessage,
    RegistrationSettingOut,
    RegistrationSettingUpdate,
    ReportCreate,
    ReportOut,
    ReportReview,
    TaskSnapshotMessage,
    TaskSnapshotOut,
    TaskSnapshotReview,
)
from app.services.auth_service import get_registration_enabled, set_registration_enabled, verify_credentials
from app.utils.user_display import display_name

_BAN_DAYS = [1, 3, 7]

router = APIRouter(prefix='/moderation', tags=['moderation'])


_BAN_TYPE_LABELS = {
    'publish': '禁止发布',
    'accept': '禁止接单',
    'contact': '禁止联系',
    'login': '封禁登录',
}

_BAN_TYPE_FIELDS = {'publish': 'ban_publish', 'accept': 'ban_accept', 'contact': 'ban_contact'}


def _ban_types_desc(types: list[str]) -> str:
    return '、'.join(_BAN_TYPE_LABELS.get(t, t) for t in types if t in _BAN_TYPE_LABELS)


def _apply_bans(
    user: User,
    ban_types: list[str],
    ban_days: int | None,
    reason: str | None,
    db: Session,
    report: 'Report | None' = None,
    is_modification: bool = False,
) -> tuple[str, int]:
    """Apply bans to user. Returns (description, actual_ban_days)."""
    has_login = 'login' in ban_types
    func_types = [t for t in ban_types if t in _BAN_TYPE_FIELDS]

    if has_login:
        user.is_banned = True
    for t in func_types:
        setattr(user, _BAN_TYPE_FIELDS[t], True)

    user.ban_reason = reason or '违反社区规则。'
    if not is_modification:
        user.ban_count = (user.ban_count or 0) + 1

    if ban_days is None:
        actual_days = _BAN_DAYS[min((user.ban_count or 1) - 1, len(_BAN_DAYS) - 1)]
    elif ban_days == 0:
        actual_days = 0
    else:
        actual_days = ban_days

    now = datetime.now(timezone.utc)
    if actual_days > 0:
        user.ban_until = now + timedelta(days=actual_days)
    else:
        user.ban_until = None

    types_desc = _ban_types_desc(ban_types)
    dur_desc = f'{actual_days} 天' if actual_days > 0 else '永久'
    desc = f'{types_desc}，时长：{dur_desc}'

    if report is not None:
        report.ban_penalty = desc

    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.type == 'punishment',
        Notification.dismiss_type == 'persistent',
    ).delete()

    notif_body = f'限制内容：{desc}'
    if user.ban_reason and user.ban_reason != '违反社区规则。':
        notif_body += f'。理由：{user.ban_reason}'
    db.add(Notification(
        user_id=user.id,
        type='punishment',
        title='账号功能受限',
        description=notif_body,
        dismiss_type='persistent',
    ))

    db.add(user)
    return desc, actual_days


def _lift_all_bans(user: User, db: Session) -> None:
    user.is_banned = False
    user.ban_reason = None
    user.ban_until = None
    user.ban_publish = False
    user.ban_accept = False
    user.ban_contact = False
    db.add(user)
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.type == 'punishment',
        Notification.dismiss_type == 'persistent',
    ).delete()


def _sync_punishment_notification(user: User, db: Session) -> None:
    has_any = bool(user.is_banned or user.ban_publish or user.ban_accept or user.ban_contact)
    current = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.type == 'punishment',
        Notification.dismiss_type == 'persistent',
    ).first()

    if not has_any:
        if current:
            db.delete(current)
        return

    labels: list[str] = []
    if user.is_banned:
        labels.append('封禁登录')
    if user.ban_publish:
        labels.append('禁止发布')
    if user.ban_accept:
        labels.append('禁止接单')
    if user.ban_contact:
        labels.append('禁止联系')
    detail = '、'.join(labels) if labels else '限制功能'
    when = f'，至 {user.ban_until.isoformat()}' if user.ban_until else '（永久）'
    desc = f'限制内容：{detail}{when}'
    if user.ban_reason:
        desc += f'。理由：{user.ban_reason}'

    if current:
        current.title = '账号功能受限'
        current.description = desc
        current.updated_at = datetime.utcnow()
        current.is_read = False
        db.add(current)
        return

    db.add(Notification(
        user_id=user.id,
        type='punishment',
        title='账号功能受限',
        description=desc,
        dismiss_type='persistent',
    ))


def _clamp_score(v: float) -> int:
    return max(0, min(100, int(round(v))))


def _safe_rate(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return part / total


def _build_user_radar(
    user: User,
    published_count: int,
    accepted_count: int,
    completed_published_count: int,
    completed_accepted_count: int,
    report_received_count: int,
    pending_report_received_count: int,
    chat_message_count: int,
) -> AdminUserRadarMetrics:
    total_rating_count = (user.publisher_rating_count or 0) + (user.worker_rating_count or 0)
    weighted_rating = 0.0
    if total_rating_count > 0:
        weighted_rating = (
            (user.publisher_rating_avg or 0) * (user.publisher_rating_count or 0)
            + (user.worker_rating_avg or 0) * (user.worker_rating_count or 0)
        ) / total_rating_count

    reliability = _clamp_score(weighted_rating / 5 * 70 + min(30, total_rating_count * 2))

    total_participation = published_count + accepted_count
    activity = _clamp_score(min(100, total_participation * 4 + min(40, chat_message_count * 0.6)))

    completed_total = completed_published_count + completed_accepted_count
    cooperation_rate = _safe_rate(completed_total, max(1, total_participation))
    cooperation = _clamp_score(cooperation_rate * 70 + min(30, total_rating_count * 2))

    risk_penalty = (
        (user.ban_count or 0) * 10
        + (user.blocked_by_count or 0) * 2
        + report_received_count * 4
        + pending_report_received_count * 6
    )
    safety = _clamp_score(100 - risk_penalty)

    account_age_days = max(1, (datetime.utcnow() - user.created_at).days)
    growth = _clamp_score(
        min(100, math.log1p(total_participation) * 25 + min(35, account_age_days / 10))
    )

    return AdminUserRadarMetrics(
        reliability=reliability,
        activity=activity,
        cooperation=cooperation,
        safety=safety,
        growth=growth,
    )


def _serialize_task_item(
    task: Task,
    users: dict[int, User],
    categories: dict[int, TaskCategory],
    report_count_map: dict[int, int],
) -> AdminTaskItem:
    publisher = users.get(task.publisher_id)
    assignee = users.get(task.assignee_id) if task.assignee_id else None
    category = categories.get(task.category_id) if task.category_id else None
    return AdminTaskItem(
        id=task.id,
        title=task.title,
        status=task.status.value,
        price=task.price,
        category_id=task.category_id,
        category_name=category.name if category else None,
        publisher_id=task.publisher_id,
        publisher_display_name=display_name(publisher) if publisher else f'用户#{task.publisher_id}',
        assignee_id=task.assignee_id,
        assignee_display_name=display_name(assignee) if assignee else None,
        is_pinned=bool(task.is_pinned),
        is_urgent=bool(task.is_urgent),
        is_deleted=bool(task.is_deleted),
        demote_level=int(task.demote_level or 0),
        deadline=task.deadline,
        created_at=task.created_at,
        updated_at=task.updated_at,
        report_count=report_count_map.get(task.id, 0),
    )


def _adjust_log_count(db: Session, user_id: int, model, user_col, ts_col, ts_field: str, target: int) -> None:
    """Adjust log entries in the 24h window to match the target count."""
    window_start = datetime.utcnow() - timedelta(hours=24)
    current = db.query(func.count(model.id)).filter(user_col == user_id, ts_col >= window_start).scalar() or 0
    if target == current:
        return
    if target < current:
        ids_to_delete = (
            db.query(model.id)
            .filter(user_col == user_id, ts_col >= window_start)
            .order_by(ts_col.asc())
            .limit(current - target)
            .all()
        )
        if ids_to_delete:
            db.query(model).filter(model.id.in_([r[0] for r in ids_to_delete])).delete(synchronize_session=False)
    elif target > current:
        for _ in range(target - current):
            entry = model(user_id=user_id, task_id=0)
            setattr(entry, ts_field, datetime.utcnow())
            db.add(entry)


def _assemble_admin_user_profile(user: User, db: Session) -> AdminUserProfileOut:
    worker = db.query(WorkerProfile).filter(WorkerProfile.user_id == user.id).first()

    published_task_count = db.query(func.count(Task.id)).filter(Task.publisher_id == user.id).scalar() or 0
    accepted_task_count = db.query(func.count(Task.id)).filter(Task.assignee_id == user.id).scalar() or 0
    completed_published_count = (
        db.query(func.count(Task.id))
        .filter(Task.publisher_id == user.id, Task.status == TaskStatus.COMPLETED)
        .scalar()
        or 0
    )
    completed_accepted_count = (
        db.query(func.count(Task.id))
        .filter(Task.assignee_id == user.id, Task.status == TaskStatus.COMPLETED)
        .scalar()
        or 0
    )
    report_submitted_count = db.query(func.count(Report.id)).filter(Report.reporter_id == user.id).scalar() or 0
    report_received_count = (
        db.query(func.count(Report.id))
        .filter(Report.reported_user_id == user.id, Report.type == ReportType.REPORT)
        .scalar()
        or 0
    )
    pending_report_received_count = (
        db.query(func.count(Report.id))
        .filter(
            Report.reported_user_id == user.id,
            Report.type == ReportType.REPORT,
            Report.status == ReportStatus.PENDING,
        )
        .scalar()
        or 0
    )
    appeal_count = (
        db.query(func.count(Report.id))
        .filter(Report.reporter_id == user.id, Report.type == ReportType.APPEAL)
        .scalar()
        or 0
    )
    chat_message_count = (
        db.query(func.count(ChatMessage.id))
        .filter(or_(ChatMessage.sender_id == user.id, ChatMessage.receiver_id == user.id))
        .scalar()
        or 0
    )

    blocked_rows = (
        db.query(Blacklist)
        .filter(Blacklist.user_id == user.id)
        .order_by(desc(Blacklist.created_at))
        .all()
    )
    blocked_ids = [r.blocked_user_id for r in blocked_rows]
    blocked_users_map = (
        {u.id: u for u in db.query(User).filter(User.id.in_(blocked_ids)).all()}
        if blocked_ids
        else {}
    )
    blocked_users = [
        AdminMiniUser(
            id=row.blocked_user_id,
            account=blocked_users_map[row.blocked_user_id].account if row.blocked_user_id in blocked_users_map else '',
            display_name=display_name(blocked_users_map[row.blocked_user_id]) if row.blocked_user_id in blocked_users_map else f'用户#{row.blocked_user_id}',
            avatar_url=blocked_users_map[row.blocked_user_id].avatar_url if row.blocked_user_id in blocked_users_map else None,
        )
        for row in blocked_rows
    ]

    recent_tasks_raw = (
        db.query(Task)
        .filter(or_(Task.publisher_id == user.id, Task.assignee_id == user.id))
        .order_by(desc(Task.updated_at))
        .limit(10)
        .all()
    )
    recent_tasks = [
        AdminUserTaskBrief(
            id=t.id,
            title=t.title,
            status=t.status.value,
            price=t.price,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in recent_tasks_raw
    ]

    recent_reports_raw = (
        db.query(Report)
        .filter(or_(Report.reporter_id == user.id, Report.reported_user_id == user.id))
        .order_by(desc(Report.created_at))
        .limit(10)
        .all()
    )
    recent_reports = [
        AdminUserReportBrief(
            id=r.id,
            type=r.type.value,
            status=r.status.value,
            reason=r.reason,
            created_at=r.created_at,
        )
        for r in recent_reports_raw
    ]

    radar = _build_user_radar(
        user=user,
        published_count=published_task_count,
        accepted_count=accepted_task_count,
        completed_published_count=completed_published_count,
        completed_accepted_count=completed_accepted_count,
        report_received_count=report_received_count,
        pending_report_received_count=pending_report_received_count,
        chat_message_count=chat_message_count,
    )

    worker_skill_ids = [t.id for t in (worker.skill_tags or [])] if worker else []
    worker_skill_names = [t.name for t in (worker.skill_tags or [])] if worker else []

    window_start = datetime.utcnow() - timedelta(hours=24)
    abandon_count_24h = (
        db.query(func.count(TaskAbandonLog.id))
        .filter(TaskAbandonLog.user_id == user.id, TaskAbandonLog.abandoned_at >= window_start)
        .scalar() or 0
    )
    cancel_count_24h = (
        db.query(func.count(TaskCancelLog.id))
        .filter(TaskCancelLog.user_id == user.id, TaskCancelLog.canceled_at >= window_start)
        .scalar() or 0
    )
    publish_count_24h = (
        db.query(func.count(TaskPublishLog.id))
        .filter(TaskPublishLog.user_id == user.id, TaskPublishLog.published_at >= window_start)
        .scalar() or 0
    )
    accept_count_24h = (
        db.query(func.count(TaskAcceptLog.id))
        .filter(TaskAcceptLog.user_id == user.id, TaskAcceptLog.accepted_at >= window_start)
        .scalar() or 0
    )

    return AdminUserProfileOut(
        id=user.id,
        account=user.account,
        name=user.name,
        nickname=user.nickname,
        email=user.email,
        gender=user.gender.value if user.gender else None,
        display_name=display_name(user),
        avatar_url=user.avatar_url,
        role=user.role.value,
        is_active=bool(user.is_active),
        is_banned=bool(user.is_banned),
        ban_reason=user.ban_reason,
        ban_count=user.ban_count or 0,
        ban_until=user.ban_until,
        ban_publish=bool(user.ban_publish),
        ban_accept=bool(user.ban_accept),
        ban_contact=bool(user.ban_contact),
        blocked_by_count=user.blocked_by_count or 0,
        last_active=user.last_active,
        created_at=user.created_at,
        worker_enabled=bool(worker.enabled) if worker else False,
        worker_bio=worker.bio if worker else None,
        worker_min_price=worker.min_price if worker else None,
        worker_max_price=worker.max_price if worker else None,
        worker_phone=worker.phone if worker else None,
        worker_wechat=worker.wechat if worker else None,
        worker_show_contact=bool(worker.show_contact) if worker else True,
        worker_skill_ids=worker_skill_ids,
        worker_skill_names=worker_skill_names,
        blocked_users=blocked_users,
        published_task_count=published_task_count,
        accepted_task_count=accepted_task_count,
        completed_published_count=completed_published_count,
        completed_accepted_count=completed_accepted_count,
        report_submitted_count=report_submitted_count,
        report_received_count=report_received_count,
        pending_report_received_count=pending_report_received_count,
        appeal_count=appeal_count,
        chat_message_count=chat_message_count,
        publisher_rating_avg=round(user.publisher_rating_avg or 0, 2),
        publisher_rating_count=user.publisher_rating_count or 0,
        worker_rating_avg=round(user.worker_rating_avg or 0, 2),
        worker_rating_count=user.worker_rating_count or 0,
        abandon_count_24h=abandon_count_24h,
        cancel_count_24h=cancel_count_24h,
        publish_count_24h=publish_count_24h,
        accept_count_24h=accept_count_24h,
        radar=radar,
        recent_tasks=recent_tasks,
        recent_reports=recent_reports,
    )


def _enrich_reports(reports: list[Report], db: Session) -> list[ReportOut]:
    user_ids: set[int] = set()
    task_ids: set[int] = set()
    for r in reports:
        user_ids.add(r.reporter_id)
        if r.reported_user_id:
            user_ids.add(r.reported_user_id)
        if r.task_id:
            task_ids.add(r.task_id)
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    tasks = {t.id: t for t in db.query(Task).filter(Task.id.in_(task_ids)).all()} if task_ids else {}
    result: list[ReportOut] = []
    for r in reports:
        out = ReportOut.model_validate(r)
        if r.task_id and r.task_id in tasks:
            out.task_title = tasks[r.task_id].title
        rp = users.get(r.reporter_id)
        if rp:
            out.reporter_name = rp.name
            out.reporter_nickname = rp.nickname
            out.reporter_account = rp.account
            out.reporter_avatar_url = rp.avatar_url
            out.reporter_gender = rp.gender.value if rp.gender else None
        ru = users.get(r.reported_user_id) if r.reported_user_id else None
        if ru:
            out.reported_user_name = ru.name
            out.reported_user_nickname = ru.nickname
            out.reported_user_account = ru.account
            out.reported_user_ban_count = ru.ban_count or 0
            out.reported_user_avatar_url = ru.avatar_url
            out.reported_user_gender = ru.gender.value if ru.gender else None
        if not out.ban_penalty and r.status == ReportStatus.APPROVED and r.type == ReportType.REPORT:
            out.ban_penalty = '已对违规方执行处罚'
        if r.is_admin_ban:
            out.reporter_name = None
            out.reporter_nickname = None
            out.reporter_account = None
            out.reporter_avatar_url = None
            out.reporter_gender = None
        result.append(out)
    return result


@router.post('/reports', response_model=ReportOut)
def create_report(
    payload: ReportCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    if not payload.reported_user_id:
        raise HTTPException(status_code=400, detail='举报必须指定被举报用户')
    if payload.reported_user_id == user.id:
        raise HTTPException(status_code=400, detail='不能举报自己')

    if payload.task_id:
        task = db.get(Task, payload.task_id)
        if not task:
            raise HTTPException(status_code=404, detail='任务不存在')
        is_publisher = task.publisher_id == user.id
        is_current_assignee = task.assignee_id == user.id
        was_assignee = (
            db.query(TaskAcceptLog)
            .filter(TaskAcceptLog.task_id == payload.task_id, TaskAcceptLog.user_id == user.id)
            .first()
        ) is not None
        if not (is_publisher or is_current_assignee or was_assignee):
            raise HTTPException(status_code=403, detail='只有任务参与者可以举报')
        reported_is_publisher = payload.reported_user_id == task.publisher_id
        reported_is_assignee = payload.reported_user_id == task.assignee_id
        reported_was_assignee = (
            db.query(TaskAcceptLog)
            .filter(TaskAcceptLog.task_id == payload.task_id, TaskAcceptLog.user_id == payload.reported_user_id)
            .first()
        ) is not None
        if not (reported_is_publisher or reported_is_assignee or reported_was_assignee):
            raise HTTPException(status_code=400, detail='被举报用户不是该任务的参与者')

        existing = (
            db.query(Report)
            .filter(
                Report.reporter_id == user.id,
                Report.task_id == payload.task_id,
                Report.reported_user_id == payload.reported_user_id,
                Report.type == ReportType.REPORT,
                Report.status == ReportStatus.PENDING,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail='该任务已有待处理的举报，请等待管理员审核')
    else:
        # 账号举报（来自接单广场，无具体任务）：每人对同一用户只能有一条待处理举报
        existing = (
            db.query(Report)
            .filter(
                Report.reporter_id == user.id,
                Report.task_id.is_(None),
                Report.reported_user_id == payload.reported_user_id,
                Report.type == ReportType.REPORT,
                Report.status == ReportStatus.PENDING,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail='已有对该用户待处理的举报，请等待管理员审核')

    report = Report(
        type=ReportType.REPORT,
        task_id=payload.task_id,
        reporter_id=user.id,
        reported_user_id=payload.reported_user_id,
        reason=payload.reason,
        evidence=payload.evidence,
        images=json.dumps(payload.images, ensure_ascii=False) if payload.images else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _enrich_reports([report], db)[0]


@router.get('/me/reports', response_model=list[ReportOut])
def list_my_reports(user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> list[ReportOut]:
    rows = db.query(Report).filter(Report.reporter_id == user.id, Report.is_admin_ban.is_(False)).order_by(desc(Report.created_at)).all()
    return _enrich_reports(rows, db)


@router.get('/me/received-reports', response_model=list[ReportOut])
def list_received_reports(user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> list[ReportOut]:
    rows = (
        db.query(Report)
        .filter(
            Report.reported_user_id == user.id,
            Report.type == ReportType.REPORT,
            Report.status == ReportStatus.APPROVED,
        )
        .order_by(desc(Report.created_at))
        .all()
    )
    enriched = _enrich_reports(rows, db)
    for r in enriched:
        r.reporter_name = None
        r.reporter_nickname = None
        r.reporter_account = None
        r.reporter_avatar_url = None
        r.reporter_gender = None
    return enriched


@router.post('/me/appeal', response_model=ReportOut)
def create_authenticated_appeal(
    payload: AuthenticatedAppealCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    has_any_ban = user.is_banned or user.ban_publish or user.ban_accept or user.ban_contact
    if not has_any_ban:
        raise HTTPException(status_code=400, detail='当前账号无任何限制，无需申诉')

    existing = (
        db.query(Report)
        .filter(Report.reporter_id == user.id, Report.type == ReportType.APPEAL, Report.status == ReportStatus.PENDING)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail='已有待处理的申诉，请等待管理员审核')

    report = Report(
        type=ReportType.APPEAL,
        reporter_id=user.id,
        reported_user_id=user.id,
        reason=payload.reason,
        evidence=payload.evidence,
        images=json.dumps(payload.images, ensure_ascii=False) if payload.images else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _enrich_reports([report], db)[0]


@router.post('/appeals', response_model=ReportOut)
def create_appeal(
    payload: AppealCreate,
    db: Session = Depends(get_db),
) -> ReportOut:
    user = verify_credentials(db, payload.account, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail='账号或密码错误')
    if not user.is_banned:
        raise HTTPException(status_code=400, detail='当前账号未被封禁，无需申诉')

    existing = (
        db.query(Report)
        .filter(Report.reporter_id == user.id, Report.type == ReportType.APPEAL, Report.status == ReportStatus.PENDING)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail='已有待处理的申诉，请等待管理员审核')

    report = Report(
        type=ReportType.APPEAL,
        reporter_id=user.id,
        reported_user_id=user.id,
        reason=payload.reason,
        evidence=payload.evidence,
        images=json.dumps(payload.images, ensure_ascii=False) if payload.images else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _enrich_reports([report], db)[0]


@router.get('/me/ban-context', response_model=BanContextOut)
def get_my_ban_context(
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> BanContextOut:
    has_any = user.is_banned or user.ban_publish or user.ban_accept or user.ban_contact
    if not has_any:
        raise HTTPException(status_code=400, detail='当前账号无任何限制')
    return _build_ban_context(user, db)


def _build_ban_context(user: User, db: Session) -> BanContextOut:
    records: list[BanRecord] = []
    approved_reports = (
        db.query(Report)
        .filter(
            Report.reported_user_id == user.id,
            Report.type == ReportType.REPORT,
            Report.status == ReportStatus.APPROVED,
        )
        .order_by(desc(Report.created_at))
        .all()
    )
    for r in approved_reports:
        records.append(
            BanRecord(source='report', reason=r.admin_notes or '违反社区规则。', created_at=r.reviewed_at or r.created_at)
        )
    admin_bans = (
        db.query(AdminActionLog)
        .filter(AdminActionLog.action == 'ban_user', AdminActionLog.target_id == str(user.id))
        .order_by(desc(AdminActionLog.created_at))
        .all()
    )
    for log in admin_bans:
        records.append(BanRecord(source='admin', reason=log.detail or '违反社区规则。', created_at=log.created_at))
    records.sort(key=lambda x: x.created_at, reverse=True)
    ban_count = user.ban_count or 0
    records = records[:ban_count]
    return BanContextOut(ban_until=user.ban_until, ban_count=ban_count, records=records)


@router.post('/ban-context', response_model=BanContextOut)
def get_ban_context(
    payload: BanContextRequest,
    db: Session = Depends(get_db),
) -> BanContextOut:
    user = verify_credentials(db, payload.account, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail='账号或密码错误')
    if not user.is_banned:
        raise HTTPException(status_code=400, detail='当前账号未被封禁')
    return _build_ban_context(user, db)


@router.post('/blacklist')
def add_blacklist(
    payload: BlacklistCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> dict:
    if payload.blocked_user_id == user.id:
        raise HTTPException(status_code=400, detail='Cannot block yourself')

    blocked = db.get(User, payload.blocked_user_id)
    if not blocked:
        raise HTTPException(status_code=404, detail='User not found')

    existing = (
        db.query(Blacklist)
        .filter(Blacklist.user_id == user.id, Blacklist.blocked_user_id == payload.blocked_user_id)
        .first()
    )
    if existing:
        return {'message': 'Already blocked'}

    record = Blacklist(user_id=user.id, blocked_user_id=payload.blocked_user_id, reason=payload.reason)
    db.add(record)
    blocked.blocked_by_count += 1
    db.add(blocked)
    db.commit()

    return {'message': 'Blocked'}


@router.get('/blacklist')
def list_blacklist(user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(Blacklist).filter(Blacklist.user_id == user.id).order_by(desc(Blacklist.created_at)).all()
    user_ids = [row.blocked_user_id for row in rows]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    return [
        {
            'blocked_user_id': row.blocked_user_id,
            'blocked_display_name': display_name(users[row.blocked_user_id])
            if row.blocked_user_id in users
            else '未知用户',
            'blocked_avatar_url': users[row.blocked_user_id].avatar_url
            if row.blocked_user_id in users
            else None,
            'reason': row.reason,
            'created_at': row.created_at,
        }
        for row in rows
    ]


@router.delete('/blacklist/{blocked_user_id}')
def remove_blacklist(
    blocked_user_id: int,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> dict:
    row = (
        db.query(Blacklist)
        .filter(Blacklist.user_id == user.id, Blacklist.blocked_user_id == blocked_user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail='Not blocked')

    blocked = db.get(User, blocked_user_id)
    if blocked and blocked.blocked_by_count > 0:
        blocked.blocked_by_count -= 1
        db.add(blocked)

    db.delete(row)
    db.commit()
    return {'message': 'Unblocked'}


@router.get('/blacklist/check/{target_user_id}')
def check_blocked(
    target_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    row = (
        db.query(Blacklist)
        .filter(Blacklist.user_id == user.id, Blacklist.blocked_user_id == target_user_id)
        .first()
    )
    return {'is_blocked': row is not None}


@router.get('/admin/reports', response_model=list[ReportOut])
def admin_list_reports(
    type: ReportType | None = Query(default=None),
    status: ReportStatus | None = Query(default=None),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    query = db.query(Report).filter(Report.is_admin_ban.is_(False))
    if type:
        query = query.filter(Report.type == type)
    if status:
        query = query.filter(Report.status == status)
    rows = query.order_by(desc(Report.created_at)).all()
    return _enrich_reports(rows, db)


@router.post('/admin/reports/{report_id}/review', response_model=ReportOut)
def admin_review_report(
    report_id: int,
    payload: ReportReview,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail='Report not found')

    report.status = payload.status
    report.admin_notes = payload.admin_notes
    report.reviewed_at = datetime.utcnow()

    if report.task_id:
        task = db.get(Task, report.task_id)
        if task and task.status == TaskStatus.UNDER_REVIEW:
            task.status = TaskStatus.IN_PROGRESS if task.assignee_id else TaskStatus.OPEN
            db.add(task)

    ban_detail = ''
    ban_desc_for_reporter = ''
    if payload.status == ReportStatus.APPROVED:
        if report.type == ReportType.REPORT and report.reported_user_id:
            reported_user = db.get(User, report.reported_user_id)
            if reported_user:
                ban_types = payload.ban_types if payload.ban_types else ['login']
                desc, actual_days = _apply_bans(reported_user, ban_types, payload.ban_days, payload.admin_notes, db, report=report)
                ban_detail = f', banned user {report.reported_user_id}: {desc}'
                ban_desc_for_reporter = desc
        elif report.type == ReportType.APPEAL:
            appealer = db.get(User, report.reporter_id)
            if appealer and (appealer.is_banned or appealer.ban_publish or appealer.ban_accept or appealer.ban_contact):
                if (appealer.ban_count or 0) > 0:
                    appealer.ban_count = appealer.ban_count - 1
                _lift_all_bans(appealer, db)
                ban_detail = f', unbanned user {report.reporter_id} (appeal approved)'

    db.add(report)
    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action='review_report',
            target_type='report',
            target_id=str(report_id),
            detail=f'status={payload.status.value}{ban_detail}',
        )
    )

    type_label = '举报' if report.type == ReportType.REPORT else '申诉'
    status_label = '已通过' if payload.status == ReportStatus.APPROVED else '已驳回'

    if report.type == ReportType.REPORT and payload.status == ReportStatus.APPROVED and ban_desc_for_reporter:
        reporter_desc = f'你的举报已通过，平台已对违规方执行以下处罚：{ban_desc_for_reporter}'
    elif report.type == ReportType.APPEAL and payload.status == ReportStatus.APPROVED:
        reporter_desc = '你的申诉已通过，相关限制已全部解除，你现在可以正常使用平台所有功能。'
    else:
        reporter_desc = f'你提交的{type_label}已被管理员审核，结果：{status_label}'

    db.add(Notification(
        user_id=report.reporter_id,
        type='report_reviewed',
        title=f'{type_label}{status_label}',
        description=reporter_desc,
        related_report_id=report.id,
        related_task_id=report.task_id,
        dismiss_type='read',
    ))

    db.commit()
    db.refresh(report)
    return _enrich_reports([report], db)[0]


@router.get('/admin/tasks/{task_id}/snapshot', response_model=TaskSnapshotOut)
def admin_task_snapshot(
    task_id: int,
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TaskSnapshotOut:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    user_ids = {task.publisher_id}
    assignee_id = task.assignee_id
    if assignee_id:
        user_ids.add(assignee_id)

    task_msgs = (
        db.query(TaskMessage)
        .filter(TaskMessage.task_id == task_id)
        .order_by(TaskMessage.created_at)
        .all()
    )
    for m in task_msgs:
        user_ids.add(m.sender_id)

    if not assignee_id:
        for m in reversed(task_msgs):
            if m.session_assignee_id:
                assignee_id = m.session_assignee_id
                user_ids.add(assignee_id)
                break

    chat_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.task_id == task_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    for cm in chat_msgs:
        user_ids.add(cm.sender_id)
        user_ids.add(cm.receiver_id)

    reviews = (
        db.query(TaskReview)
        .filter(TaskReview.task_id == task_id)
        .order_by(TaskReview.created_at)
        .all()
    )
    for r in reviews:
        user_ids.add(r.reviewer_id)

    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    dn = lambda uid: display_name(users.get(uid)) if users.get(uid) else '未知用户'

    merged_messages: list[TaskSnapshotMessage] = []
    for m in task_msgs:
        merged_messages.append(TaskSnapshotMessage(
            sender_display_name=dn(m.sender_id),
            content=m.content,
            created_at=m.created_at,
        ))
    for cm in chat_msgs:
        merged_messages.append(TaskSnapshotMessage(
            sender_display_name=dn(cm.sender_id),
            content=cm.content,
            created_at=cm.created_at,
        ))
    merged_messages.sort(key=lambda msg: msg.created_at)

    return TaskSnapshotOut(
        id=task.id,
        title=task.title,
        description=task.description,
        deadline=task.deadline,
        location=task.location,
        price=task.price,
        status=task.status.value,
        is_deleted=bool(task.is_deleted),
        publisher_display_name=dn(task.publisher_id),
        assignee_display_name=dn(assignee_id) if assignee_id else None,
        created_at=task.created_at,
        messages=merged_messages,
        reviews=[
            TaskSnapshotReview(
                reviewer_display_name=dn(r.reviewer_id),
                target_role=r.target_role.value,
                stars=r.stars,
                comment=r.comment,
                created_at=r.created_at,
            )
            for r in reviews
        ],
    )


@router.get('/admin/reports/{report_id}/chat-history', response_model=DirectChatHistoryOut)
def admin_report_chat_history(
    report_id: int,
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DirectChatHistoryOut:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail='Report not found')
    if not report.reported_user_id:
        raise HTTPException(status_code=400, detail='该举报无被举报用户')

    user_a = report.reporter_id
    user_b = report.reported_user_id
    task_filter = (
        ChatMessage.task_id == report.task_id
        if report.task_id is not None
        else ChatMessage.task_id.is_(None)
    )

    messages = (
        db.query(ChatMessage)
        .filter(
            or_(
                and_(ChatMessage.sender_id == user_a, ChatMessage.receiver_id == user_b),
                and_(ChatMessage.sender_id == user_b, ChatMessage.receiver_id == user_a),
            ),
            task_filter,
        )
        .order_by(ChatMessage.created_at)
        .all()
    )

    users = {u.id: u for u in db.query(User).filter(User.id.in_([user_a, user_b])).all()}
    dn = lambda uid: display_name(users.get(uid)) if users.get(uid) else '未知用户'

    return DirectChatHistoryOut(
        reporter_display_name=dn(user_a),
        reported_user_display_name=dn(user_b),
        messages=[
            DirectChatMessage(
                sender_display_name=dn(m.sender_id),
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.post('/admin/users/{user_id}/ban')
def admin_ban_user(
    user_id: int,
    payload: BanUserRequest,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    has_active_ban = user.is_banned or user.ban_publish or user.ban_accept or user.ban_contact
    is_modification = has_active_ban and payload.banned

    if payload.banned:
        ban_types = payload.ban_types if payload.ban_types else ['login']

        if is_modification:
            user.is_banned = False
            user.ban_publish = False
            user.ban_accept = False
            user.ban_contact = False

        existing_report = (
            db.query(Report)
            .filter(
                Report.reported_user_id == user_id,
                Report.is_admin_ban.is_(True),
                Report.status == ReportStatus.APPROVED,
            )
            .order_by(desc(Report.created_at))
            .first()
        ) if is_modification else None

        if existing_report:
            penalty_report = existing_report
            penalty_report.admin_notes = payload.reason
            penalty_report.reason = payload.reason or '管理员封禁'
            penalty_report.reviewed_at = datetime.utcnow()
        else:
            penalty_report = Report(
                type=ReportType.REPORT,
                reporter_id=user_id,
                reported_user_id=user_id,
                reason=payload.reason or '管理员封禁',
                evidence='',
                status=ReportStatus.APPROVED,
                admin_notes=payload.reason,
                is_admin_ban=True,
                reviewed_at=datetime.utcnow(),
            )
            db.add(penalty_report)
            db.flush()

        ban_desc, _ = _apply_bans(user, ban_types, payload.ban_days, payload.reason, db, report=penalty_report, is_modification=is_modification)
        action = 'ban_user' if not is_modification else 'modify_ban'
        detail = ban_desc
    else:
        if payload.innocent and (user.ban_count or 0) > 0:
            user.ban_count = user.ban_count - 1
        _lift_all_bans(user, db)
        action = 'unban_user_innocent' if payload.innocent else 'unban_user'
        detail = '无责解封' if payload.innocent else '有责解封'

    db.add(user)
    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action=action,
            target_type='user',
            target_id=str(user_id),
            detail=detail,
        )
    )
    db.commit()
    return {
        'message': 'ok',
        'ban_until': user.ban_until.isoformat() if user.ban_until else None,
        'ban_count': user.ban_count or 0,
    }


@router.get('/admin/users', response_model=AdminUserListResponse)
def admin_list_users(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserListResponse:
    query = db.query(User)
    if q and q.strip():
        like = f'%{q.strip()}%'
        query = query.filter(
            or_(
                User.account.like(like),
                User.name.like(like),
                User.nickname.like(like),
            )
        )
    total = query.count()
    items = query.order_by(desc(User.created_at), desc(User.id)).offset((page - 1) * page_size).limit(page_size).all()

    user_ids = [u.id for u in items]
    profile_rows = db.query(WorkerProfile).filter(WorkerProfile.user_id.in_(user_ids)).all() if user_ids else []
    profile_map = {p.user_id: p for p in profile_rows}
    profile_ids = [p.id for p in profile_rows]
    skill_count_by_profile: dict[int, int] = {}
    if profile_ids:
        skill_count_by_profile = dict(
            db.query(worker_skill_tags.c.worker_profile_id, func.count(worker_skill_tags.c.skill_tag_id))
            .filter(worker_skill_tags.c.worker_profile_id.in_(profile_ids))
            .group_by(worker_skill_tags.c.worker_profile_id)
            .all()
        )

    published_map = {}
    accepted_map = {}
    completed_pub_map = {}
    completed_accept_map = {}
    report_received_map = {}
    publish_24h_map = {}
    accept_24h_map = {}
    if user_ids:
        published_map = dict(
            db.query(Task.publisher_id, func.count(Task.id))
            .filter(Task.publisher_id.in_(user_ids))
            .group_by(Task.publisher_id)
            .all()
        )
        accepted_map = dict(
            db.query(Task.assignee_id, func.count(Task.id))
            .filter(Task.assignee_id.in_(user_ids))
            .group_by(Task.assignee_id)
            .all()
        )
        completed_pub_map = dict(
            db.query(Task.publisher_id, func.count(Task.id))
            .filter(Task.publisher_id.in_(user_ids), Task.status == TaskStatus.COMPLETED)
            .group_by(Task.publisher_id)
            .all()
        )
        completed_accept_map = dict(
            db.query(Task.assignee_id, func.count(Task.id))
            .filter(Task.assignee_id.in_(user_ids), Task.status == TaskStatus.COMPLETED)
            .group_by(Task.assignee_id)
            .all()
        )
        report_received_map = dict(
            db.query(Report.reported_user_id, func.count(Report.id))
            .filter(Report.reported_user_id.in_(user_ids), Report.type == ReportType.REPORT)
            .group_by(Report.reported_user_id)
            .all()
        )
        window_start_24h = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        publish_24h_map = dict(
            db.query(TaskPublishLog.user_id, func.count(TaskPublishLog.id))
            .filter(TaskPublishLog.user_id.in_(user_ids), TaskPublishLog.published_at >= window_start_24h)
            .group_by(TaskPublishLog.user_id)
            .all()
        )
        accept_24h_map = dict(
            db.query(TaskAcceptLog.user_id, func.count(TaskAcceptLog.id))
            .filter(TaskAcceptLog.user_id.in_(user_ids), TaskAcceptLog.accepted_at >= window_start_24h)
            .group_by(TaskAcceptLog.user_id)
            .all()
        )

    return AdminUserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            (
                lambda profile: AdminUserItem(
                    id=u.id,
                    account=u.account,
                    name=u.name,
                    nickname=u.nickname,
                    email=u.email,
                    gender=u.gender.value if u.gender else None,
                    display_name=display_name(u),
                    avatar_url=u.avatar_url,
                    role=u.role.value,
                    is_active=bool(u.is_active),
                    is_banned=u.is_banned,
                    ban_reason=u.ban_reason,
                    ban_count=u.ban_count or 0,
                    ban_until=u.ban_until,
                    ban_publish=u.ban_publish or False,
                    ban_accept=u.ban_accept or False,
                    ban_contact=u.ban_contact or False,
                    blocked_by_count=u.blocked_by_count or 0,
                    worker_enabled=bool(profile.enabled) if profile else False,
                    worker_skill_count=skill_count_by_profile.get(profile.id, 0) if profile else 0,
                    publisher_rating_avg=round(u.publisher_rating_avg or 0, 2),
                    publisher_rating_count=u.publisher_rating_count or 0,
                    worker_rating_avg=round(u.worker_rating_avg or 0, 2),
                    worker_rating_count=u.worker_rating_count or 0,
                    published_task_count=published_map.get(u.id, 0),
                    accepted_task_count=accepted_map.get(u.id, 0),
                    completed_task_count=completed_pub_map.get(u.id, 0) + completed_accept_map.get(u.id, 0),
                    report_received_count=report_received_map.get(u.id, 0),
                    publish_count_24h=publish_24h_map.get(u.id, 0),
                    accept_count_24h=accept_24h_map.get(u.id, 0),
                    last_active=u.last_active,
                    created_at=u.created_at,
                )
            )(profile_map.get(u.id))
            for u in items
        ],
    )


@router.get('/admin/users/{user_id}/profile', response_model=AdminUserProfileOut)
def admin_get_user_profile(
    user_id: int,
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserProfileOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return _assemble_admin_user_profile(user, db)


@router.put('/admin/users/{user_id}/profile', response_model=AdminUserProfileOut)
def admin_update_user_profile(
    user_id: int,
    payload: AdminUserUpdateRequest,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserProfileOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    data = payload.model_dump(exclude_unset=True)

    if 'name' in data:
        user.name = (data.get('name') or '').strip() or user.name
    if 'nickname' in data:
        nickname = data.get('nickname')
        user.nickname = nickname.strip() if isinstance(nickname, str) and nickname.strip() else None
    if 'email' in data:
        email = data.get('email')
        user.email = email.strip() if isinstance(email, str) and email.strip() else None
    if 'gender' in data:
        gender = data.get('gender')
        user.gender = Gender(gender) if gender else None
    if 'role' in data:
        role_value = data.get('role')
        user.role = UserRole(role_value) if role_value else user.role
    if 'is_active' in data:
        user.is_active = bool(data.get('is_active'))

    for field in ('is_banned', 'ban_publish', 'ban_accept', 'ban_contact'):
        if field in data:
            setattr(user, field, bool(data.get(field)))

    if 'ban_reason' in data:
        user.ban_reason = data.get('ban_reason') or None
    if 'ban_until' in data:
        user.ban_until = data.get('ban_until')
    if 'ban_count' in data:
        user.ban_count = data.get('ban_count') or 0
    if 'blocked_by_count' in data:
        user.blocked_by_count = data.get('blocked_by_count') or 0

    if 'abandon_count_24h' in data:
        _adjust_log_count(
            db, user.id, TaskAbandonLog, TaskAbandonLog.user_id,
            TaskAbandonLog.abandoned_at, 'abandoned_at',
            int(data.get('abandon_count_24h') or 0),
        )
    if 'cancel_count_24h' in data:
        _adjust_log_count(
            db, user.id, TaskCancelLog, TaskCancelLog.user_id,
            TaskCancelLog.canceled_at, 'canceled_at',
            int(data.get('cancel_count_24h') or 0),
        )
    if 'accept_count_24h' in data:
        _adjust_log_count(
            db, user.id, TaskAcceptLog, TaskAcceptLog.user_id,
            TaskAcceptLog.accepted_at, 'accepted_at',
            int(data.get('accept_count_24h') or 0),
        )
    if 'publish_count_24h' in data:
        _adjust_log_count(
            db, user.id, TaskPublishLog, TaskPublishLog.user_id,
            TaskPublishLog.published_at, 'published_at',
            int(data.get('publish_count_24h') or 0),
        )

    if not (user.is_banned or user.ban_publish or user.ban_accept or user.ban_contact):
        user.ban_until = None
        if 'ban_reason' not in data:
            user.ban_reason = None

    worker_related = any(
        k in data
        for k in (
            'worker_enabled',
            'worker_bio',
            'worker_min_price',
            'worker_max_price',
            'worker_phone',
            'worker_wechat',
            'worker_show_contact',
            'worker_skill_tag_ids',
        )
    )
    worker = db.query(WorkerProfile).filter(WorkerProfile.user_id == user.id).first()
    if worker_related and not worker:
        worker = WorkerProfile(user_id=user.id)

    if worker:
        if 'worker_enabled' in data:
            worker.enabled = bool(data.get('worker_enabled'))
        if 'worker_bio' in data:
            worker.bio = data.get('worker_bio') or None
        if 'worker_min_price' in data:
            worker.min_price = data.get('worker_min_price')
        if 'worker_max_price' in data:
            worker.max_price = data.get('worker_max_price')
        if worker.min_price is not None and worker.max_price is not None and worker.min_price > worker.max_price:
            raise HTTPException(status_code=422, detail='worker_min_price cannot exceed worker_max_price')
        if 'worker_phone' in data:
            phone = data.get('worker_phone')
            worker.phone = phone.strip() if isinstance(phone, str) and phone.strip() else None
        if 'worker_wechat' in data:
            wechat = data.get('worker_wechat')
            worker.wechat = wechat.strip() if isinstance(wechat, str) and wechat.strip() else None
        if 'worker_show_contact' in data:
            worker.show_contact = bool(data.get('worker_show_contact'))
        if 'worker_skill_tag_ids' in data:
            skill_ids = data.get('worker_skill_tag_ids') or []
            if len(skill_ids) > 8:
                raise HTTPException(status_code=422, detail='最多选择 8 个技能类别')
            if skill_ids:
                tags = db.query(TaskCategory).filter(TaskCategory.id.in_(skill_ids)).all()
                if len(tags) != len(skill_ids):
                    raise HTTPException(status_code=422, detail='部分类别不存在')
                worker.skill_tags = tags
            else:
                worker.skill_tags = []
            worker.skills = '、'.join(t.name for t in worker.skill_tags) if worker.skill_tags else None
        db.add(worker)

    _sync_punishment_notification(user, db)
    db.add(user)
    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action='update_user_profile',
            target_type='user',
            target_id=str(user.id),
            detail='管理员修改了用户资料/风控信息',
        )
    )
    db.commit()
    db.refresh(user)
    return _assemble_admin_user_profile(user, db)


@router.get('/admin/users/{user_id}/blacklist', response_model=list[AdminBlacklistItem])
def admin_list_user_blacklist(
    user_id: int,
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminBlacklistItem]:
    owner = db.get(User, user_id)
    if not owner:
        raise HTTPException(status_code=404, detail='User not found')
    rows = db.query(Blacklist).filter(Blacklist.user_id == user_id).order_by(desc(Blacklist.created_at)).all()
    blocked_ids = [r.blocked_user_id for r in rows]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(blocked_ids)).all()} if blocked_ids else {}
    return [
        AdminBlacklistItem(
            blocked_user_id=r.blocked_user_id,
            blocked_display_name=display_name(users[r.blocked_user_id]) if r.blocked_user_id in users else f'用户#{r.blocked_user_id}',
            blocked_account=users[r.blocked_user_id].account if r.blocked_user_id in users else '',
            blocked_avatar_url=users[r.blocked_user_id].avatar_url if r.blocked_user_id in users else None,
            reason=r.reason,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post('/admin/users/{user_id}/blacklist', response_model=list[AdminBlacklistItem])
def admin_add_user_blacklist(
    user_id: int,
    payload: BlacklistCreate,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminBlacklistItem]:
    owner = db.get(User, user_id)
    if not owner:
        raise HTTPException(status_code=404, detail='User not found')
    if payload.blocked_user_id == user_id:
        raise HTTPException(status_code=400, detail='Cannot block self')
    target = db.get(User, payload.blocked_user_id)
    if not target:
        raise HTTPException(status_code=404, detail='Blocked user not found')

    exists = (
        db.query(Blacklist)
        .filter(Blacklist.user_id == user_id, Blacklist.blocked_user_id == payload.blocked_user_id)
        .first()
    )
    if not exists:
        db.add(Blacklist(user_id=user_id, blocked_user_id=payload.blocked_user_id, reason=payload.reason))
        target.blocked_by_count = (target.blocked_by_count or 0) + 1
        db.add(target)
        db.add(
            AdminActionLog(
                admin_identifier=admin.admin_account or 'admin',
                action='admin_add_blacklist',
                target_type='user',
                target_id=str(user_id),
                detail=f'blocked_user_id={payload.blocked_user_id}',
            )
        )
        db.commit()

    return admin_list_user_blacklist(user_id=user_id, _admin=admin, db=db)


@router.delete('/admin/users/{user_id}/blacklist/{blocked_user_id}', response_model=list[AdminBlacklistItem])
def admin_remove_user_blacklist(
    user_id: int,
    blocked_user_id: int,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminBlacklistItem]:
    owner = db.get(User, user_id)
    if not owner:
        raise HTTPException(status_code=404, detail='User not found')

    row = (
        db.query(Blacklist)
        .filter(Blacklist.user_id == user_id, Blacklist.blocked_user_id == blocked_user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail='Blacklist item not found')

    blocked = db.get(User, blocked_user_id)
    if blocked and (blocked.blocked_by_count or 0) > 0:
        blocked.blocked_by_count = blocked.blocked_by_count - 1
        db.add(blocked)
    db.delete(row)
    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action='admin_remove_blacklist',
            target_type='user',
            target_id=str(user_id),
            detail=f'blocked_user_id={blocked_user_id}',
        )
    )
    db.commit()
    return admin_list_user_blacklist(user_id=user_id, _admin=admin, db=db)


@router.get('/admin/tasks', response_model=AdminTaskListResponse)
def admin_list_tasks(
    q: str | None = Query(default=None),
    status: TaskStatus | None = Query(default=None),
    publisher_id: int | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    flag: str | None = Query(default=None, pattern='^(pinned|urgent|flagged)$'),
    deleted: bool | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=40, ge=1, le=100),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminTaskListResponse:
    query = db.query(Task)
    if q and q.strip():
        like = f'%{q.strip()}%'
        query = query.filter(or_(Task.title.like(like), Task.description.like(like), Task.location.like(like)))
    if status:
        query = query.filter(Task.status == status)
    if publisher_id is not None:
        query = query.filter(Task.publisher_id == publisher_id)
    if assignee_id is not None:
        if assignee_id == 0:
            query = query.filter(Task.assignee_id.is_(None))
        else:
            query = query.filter(Task.assignee_id == assignee_id)
    if flag == 'pinned':
        query = query.filter(Task.is_pinned.is_(True))
    elif flag == 'urgent':
        query = query.filter(Task.is_urgent.is_(True))
    elif flag == 'flagged':
        query = query.filter(or_(Task.is_pinned.is_(True), Task.is_urgent.is_(True)))
    if deleted is True:
        query = query.filter(Task.is_deleted.is_(True))
    elif deleted is False:
        query = query.filter(Task.is_deleted.is_(False))
    if overdue is True:
        now = datetime.utcnow()
        query = query.filter(Task.deadline.isnot(None), Task.deadline < now)
    elif overdue is False:
        now = datetime.utcnow()
        query = query.filter(or_(Task.deadline.is_(None), Task.deadline >= now))

    total = query.count()
    rows = (
        query.order_by(desc(Task.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    task_ids = [t.id for t in rows]
    user_ids = {t.publisher_id for t in rows}
    user_ids.update({t.assignee_id for t in rows if t.assignee_id})
    cat_ids = {t.category_id for t in rows if t.category_id}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    categories = {c.id: c for c in db.query(TaskCategory).filter(TaskCategory.id.in_(cat_ids)).all()} if cat_ids else {}
    report_count_map = (
        dict(
            db.query(Report.task_id, func.count(Report.id))
            .filter(Report.task_id.in_(task_ids), Report.type == ReportType.REPORT)
            .group_by(Report.task_id)
            .all()
        )
        if task_ids
        else {}
    )

    return AdminTaskListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_serialize_task_item(task=t, users=users, categories=categories, report_count_map=report_count_map) for t in rows],
    )


@router.post('/admin/tasks/{task_id}/operate')
def admin_operate_task(
    task_id: int,
    payload: AdminTaskOperateRequest,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    if payload.delete:
        title = task.title
        publisher_id = task.publisher_id
        assignee_id = task.assignee_id

        task.is_deleted = True
        task.deleted_at = datetime.utcnow()
        db.add(task)

        db.add(Notification(
            user_id=publisher_id,
            type='admin_task_notice',
            title='任务已被管理员删除',
            description=f'你的任务「{title}」已被管理员删除，如有疑问请联系平台。',
            related_task_id=task_id,
            dismiss_type='read',
        ))
        if assignee_id:
            db.add(Notification(
                user_id=assignee_id,
                type='admin_task_notice',
                title='你参与的任务已被管理员删除',
                description=f'任务「{title}」已被管理员删除，如有疑问请联系平台。',
                related_task_id=task_id,
                dismiss_type='read',
            ))

        db.add(
            AdminActionLog(
                admin_identifier=admin.admin_account or 'admin',
                action='admin_delete_task',
                target_type='task',
                target_id=str(task_id),
                detail=f'title={title}',
            )
        )
        db.commit()
        return {'message': 'deleted', 'deleted': True}

    changed: list[str] = []
    notify_parts: list[str] = []
    if payload.set_pinned is not None and bool(task.is_pinned) != bool(payload.set_pinned):
        task.is_pinned = bool(payload.set_pinned)
        changed.append(f'is_pinned={task.is_pinned}')
        notify_parts.append('置顶' if task.is_pinned else '取消置顶')
    if payload.set_urgent is not None and bool(task.is_urgent) != bool(payload.set_urgent):
        task.is_urgent = bool(payload.set_urgent)
        changed.append(f'is_urgent={task.is_urgent}')
        notify_parts.append('加急' if task.is_urgent else '取消加急')
    if payload.set_demote_level is not None and int(task.demote_level or 0) != payload.set_demote_level:
        task.demote_level = payload.set_demote_level
        changed.append(f'demote_level={task.demote_level}')

    if not changed:
        raise HTTPException(status_code=400, detail='No task operation provided')

    db.add(task)

    if notify_parts:
        action_desc = '、'.join(notify_parts)
        if task.publisher_id:
            db.add(Notification(
                user_id=task.publisher_id,
                type='admin_task_notice',
                title=f'你的任务「{task.title}」已被管理员{action_desc}',
                description=f'管理员已将你的任务「{task.title}」设为{action_desc}，该操作可能影响任务在大厅中的展示顺序。如有疑问请联系平台。',
                related_task_id=task.id,
                dismiss_type='read',
            ))
        if task.assignee_id:
            db.add(Notification(
                user_id=task.assignee_id,
                type='admin_task_notice',
                title=f'你参与的任务「{task.title}」已被管理员{action_desc}',
                description=f'你参与的任务「{task.title}」已被管理员设为{action_desc}，该操作可能影响任务在大厅中的展示顺序。如有疑问请联系平台。',
                related_task_id=task.id,
                dismiss_type='read',
            ))
    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action='admin_update_task',
            target_type='task',
            target_id=str(task.id),
            detail='; '.join(changed),
        )
    )
    db.commit()
    db.refresh(task)

    users = {
        u.id: u
        for u in db.query(User).filter(User.id.in_([task.publisher_id] + ([task.assignee_id] if task.assignee_id else []))).all()
    }
    categories = (
        {c.id: c for c in db.query(TaskCategory).filter(TaskCategory.id == task.category_id).all()}
        if task.category_id
        else {}
    )
    report_count_map = dict(
        db.query(Report.task_id, func.count(Report.id))
        .filter(Report.task_id == task.id, Report.type == ReportType.REPORT)
        .group_by(Report.task_id)
        .all()
    )
    item = _serialize_task_item(task=task, users=users, categories=categories, report_count_map=report_count_map)
    return {'message': 'updated', 'deleted': False, 'item': item.model_dump()}


@router.get('/admin/chats', response_model=AdminChatConversationListResponse)
def admin_list_chat_conversations(
    q: str | None = Query(default=None),
    task_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminChatConversationListResponse:
    low_uid = case(
        (ChatMessage.sender_id < ChatMessage.receiver_id, ChatMessage.sender_id),
        else_=ChatMessage.receiver_id,
    )
    high_uid = case(
        (ChatMessage.sender_id < ChatMessage.receiver_id, ChatMessage.receiver_id),
        else_=ChatMessage.sender_id,
    )

    grouped = db.query(
        low_uid.label('user_a_id'),
        high_uid.label('user_b_id'),
        ChatMessage.task_id.label('task_id'),
        func.count(ChatMessage.id).label('message_count'),
        func.max(ChatMessage.created_at).label('last_message_time'),
    )

    if q and q.strip():
        grouped = grouped.filter(ChatMessage.content.like(f'%{q.strip()}%'))
    if task_id is not None:
        if task_id == 0:
            grouped = grouped.filter(ChatMessage.task_id.is_(None))
        elif task_id == -1:
            grouped = grouped.filter(ChatMessage.task_id.isnot(None))
        else:
            grouped = grouped.filter(ChatMessage.task_id == task_id)
    if user_id is not None:
        grouped = grouped.filter(or_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == user_id))

    grouped = grouped.group_by(low_uid, high_uid, ChatMessage.task_id).subquery()
    total = db.query(func.count()).select_from(grouped).scalar() or 0
    rows = (
        db.query(grouped)
        .order_by(desc(grouped.c.last_message_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    user_ids = {r.user_a_id for r in rows} | {r.user_b_id for r in rows}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    task_ids = {r.task_id for r in rows if r.task_id}
    tasks = {t.id: t for t in db.query(Task).filter(Task.id.in_(task_ids)).all()} if task_ids else {}

    items: list[AdminChatConversationItem] = []
    for r in rows:
        task_filter = ChatMessage.task_id == r.task_id if r.task_id is not None else ChatMessage.task_id.is_(None)
        last_msg = (
            db.query(ChatMessage)
            .filter(
                or_(
                    and_(ChatMessage.sender_id == r.user_a_id, ChatMessage.receiver_id == r.user_b_id),
                    and_(ChatMessage.sender_id == r.user_b_id, ChatMessage.receiver_id == r.user_a_id),
                ),
                task_filter,
            )
            .order_by(desc(ChatMessage.created_at), desc(ChatMessage.id))
            .first()
        )
        u1 = users.get(r.user_a_id)
        u2 = users.get(r.user_b_id)
        task_obj = tasks.get(r.task_id) if r.task_id else None
        items.append(AdminChatConversationItem(
            user_a_id=r.user_a_id,
            user_a_display_name=display_name(u1) if u1 else f'用户#{r.user_a_id}',
            user_a_avatar_url=u1.avatar_url if u1 else None,
            user_a_gender=u1.gender.value if u1 and u1.gender else None,
            user_b_id=r.user_b_id,
            user_b_display_name=display_name(u2) if u2 else f'用户#{r.user_b_id}',
            user_b_avatar_url=u2.avatar_url if u2 else None,
            user_b_gender=u2.gender.value if u2 and u2.gender else None,
            task_id=r.task_id,
            task_title=task_obj.title if task_obj else None,
            task_price=task_obj.price if task_obj else None,
            task_status=task_obj.status.value if task_obj and task_obj.status else None,
            message_count=int(r.message_count or 0),
            last_message=last_msg.content if last_msg else None,
            last_message_time=last_msg.created_at if last_msg else r.last_message_time,
        ))

    return AdminChatConversationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get('/admin/chats/messages', response_model=list[AdminChatMessageOut])
def admin_list_chat_messages(
    user_a_id: int,
    user_b_id: int,
    task_id: int | None = Query(default=None),
    before_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminChatMessageOut]:
    task_filter = ChatMessage.task_id == task_id if task_id is not None else ChatMessage.task_id.is_(None)
    query = db.query(ChatMessage).filter(
        or_(
            and_(ChatMessage.sender_id == user_a_id, ChatMessage.receiver_id == user_b_id),
            and_(ChatMessage.sender_id == user_b_id, ChatMessage.receiver_id == user_a_id),
        ),
        task_filter,
    )
    if before_id is not None:
        query = query.filter(ChatMessage.id < before_id)
    rows = query.order_by(desc(ChatMessage.id)).limit(limit).all()
    rows.reverse()

    users = {
        u.id: u
        for u in db.query(User).filter(User.id.in_([user_a_id, user_b_id])).all()
    }
    return [
        AdminChatMessageOut(
            id=m.id,
            sender_id=m.sender_id,
            sender_display_name=display_name(users[m.sender_id]) if m.sender_id in users else f'用户#{m.sender_id}',
            sender_avatar_url=users[m.sender_id].avatar_url if m.sender_id in users else None,
            sender_gender=users[m.sender_id].gender.value if m.sender_id in users and users[m.sender_id].gender else None,
            receiver_id=m.receiver_id,
            receiver_display_name=display_name(users[m.receiver_id]) if m.receiver_id in users else f'用户#{m.receiver_id}',
            task_id=m.task_id,
            content=m.content,
            is_read=bool(m.is_read),
            blocked=bool(m.blocked),
            created_at=m.created_at,
        )
        for m in rows
    ]


@router.get('/admin/task-chats', response_model=AdminTaskChatConversationListResponse)
def admin_list_task_chat_conversations(
    q: str | None = Query(default=None),
    task_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminTaskChatConversationListResponse:
    grouped = db.query(
        TaskMessage.task_id.label('task_id'),
        TaskMessage.session_assignee_id.label('session_assignee_id'),
        func.count(TaskMessage.id).label('message_count'),
        func.max(TaskMessage.created_at).label('last_message_time'),
    )
    if q and q.strip():
        grouped = grouped.filter(TaskMessage.content.like(f'%{q.strip()}%'))
    if task_id is not None:
        grouped = grouped.filter(TaskMessage.task_id == task_id)

    grouped = grouped.group_by(TaskMessage.task_id, TaskMessage.session_assignee_id).subquery()
    total = db.query(func.count()).select_from(grouped).scalar() or 0
    rows = (
        db.query(grouped)
        .order_by(desc(grouped.c.last_message_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    task_ids = {r.task_id for r in rows}
    tasks = {t.id: t for t in db.query(Task).filter(Task.id.in_(task_ids)).all()} if task_ids else {}
    user_ids: set[int] = set()
    for row in rows:
        task_obj = tasks.get(row.task_id)
        if task_obj:
            user_ids.add(task_obj.publisher_id)
        if row.session_assignee_id:
            user_ids.add(row.session_assignee_id)
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    items: list[AdminTaskChatConversationItem] = []
    for row in rows:
        task_obj = tasks.get(row.task_id)
        if not task_obj:
            continue

        session_filter = (
            TaskMessage.session_assignee_id == row.session_assignee_id
            if row.session_assignee_id is not None
            else TaskMessage.session_assignee_id.is_(None)
        )
        last_msg = (
            db.query(TaskMessage)
            .filter(TaskMessage.task_id == row.task_id, session_filter)
            .order_by(desc(TaskMessage.created_at), desc(TaskMessage.id))
            .first()
        )

        publisher = users.get(task_obj.publisher_id)
        session_assignee = users.get(row.session_assignee_id) if row.session_assignee_id else None
        items.append(AdminTaskChatConversationItem(
            task_id=task_obj.id,
            task_title=task_obj.title,
            task_price=task_obj.price,
            task_status=task_obj.status.value if task_obj.status else None,
            publisher_id=task_obj.publisher_id,
            publisher_display_name=display_name(publisher) if publisher else f'用户#{task_obj.publisher_id}',
            publisher_avatar_url=publisher.avatar_url if publisher else None,
            publisher_gender=publisher.gender.value if publisher and publisher.gender else None,
            session_assignee_id=row.session_assignee_id,
            session_assignee_display_name=display_name(session_assignee) if session_assignee else None,
            session_assignee_avatar_url=session_assignee.avatar_url if session_assignee else None,
            session_assignee_gender=session_assignee.gender.value if session_assignee and session_assignee.gender else None,
            message_count=int(row.message_count or 0),
            last_message=last_msg.content if last_msg else None,
            last_message_time=last_msg.created_at if last_msg else row.last_message_time,
        ))

    return AdminTaskChatConversationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get('/admin/task-chats/messages', response_model=list[AdminTaskChatMessageOut])
def admin_list_task_chat_messages(
    task_id: int,
    session_assignee_id: int | None = Query(default=None),
    null_session: bool = Query(default=False),
    before_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminTaskChatMessageOut]:
    query = db.query(TaskMessage).filter(TaskMessage.task_id == task_id)
    if null_session:
        query = query.filter(TaskMessage.session_assignee_id.is_(None))
    elif session_assignee_id is not None:
        query = query.filter(TaskMessage.session_assignee_id == session_assignee_id)
    if before_id is not None:
        query = query.filter(TaskMessage.id < before_id)
    rows = query.order_by(desc(TaskMessage.id)).limit(limit).all()
    rows.reverse()

    sender_ids = {m.sender_id for m in rows}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(sender_ids)).all()} if sender_ids else {}
    return [
        AdminTaskChatMessageOut(
            id=m.id,
            task_id=m.task_id,
            sender_id=m.sender_id,
            sender_display_name=display_name(users[m.sender_id]) if m.sender_id in users else f'用户#{m.sender_id}',
            sender_avatar_url=users[m.sender_id].avatar_url if m.sender_id in users else None,
            sender_gender=users[m.sender_id].gender.value if m.sender_id in users and users[m.sender_id].gender else None,
            session_assignee_id=m.session_assignee_id,
            content=m.content,
            created_at=m.created_at,
        )
        for m in rows
    ]


@router.get('/admin/chats/attachments', response_model=list[AdminChatAttachmentOut])
def admin_list_chat_attachments(
    user_a_id: int,
    user_b_id: int,
    task_id: int | None = Query(default=None),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminChatAttachmentOut]:
    lo, hi = (min(user_a_id, user_b_id), max(user_a_id, user_b_id))
    task_filter = ChatAttachment.task_id == task_id if task_id is not None else ChatAttachment.task_id.is_(None)
    rows = (
        db.query(ChatAttachment)
        .filter(
            or_(
                and_(ChatAttachment.uploader_id == lo, ChatAttachment.peer_id == hi),
                and_(ChatAttachment.uploader_id == hi, ChatAttachment.peer_id == lo),
            ),
            task_filter,
        )
        .order_by(ChatAttachment.created_at)
        .all()
    )
    return [
        AdminChatAttachmentOut(
            id=a.id,
            message_id=a.message_id,
            file_name=a.file_name,
            file_url=a.file_url,
            file_size=a.file_size,
            mime_type=a.mime_type,
        )
        for a in rows
    ]


@router.post('/admin/notifications/push', response_model=AdminPushNotificationOut)
def admin_push_notification(
    payload: AdminPushNotificationRequest,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminPushNotificationOut:
    target_ids: set[int] = set(payload.user_ids)
    now = datetime.utcnow()

    if payload.include_all:
        ids = db.query(User.id).filter(User.role == UserRole.USER).all()
        target_ids.update({row[0] for row in ids})
    if payload.include_banned:
        ids = (
            db.query(User.id)
            .filter(
                User.role == UserRole.USER,
                or_(User.is_banned.is_(True), User.ban_publish.is_(True), User.ban_accept.is_(True), User.ban_contact.is_(True)),
            )
            .all()
        )
        target_ids.update({row[0] for row in ids})
    if payload.include_recent_active:
        cutoff = now - timedelta(days=3)
        ids = db.query(User.id).filter(User.role == UserRole.USER, User.last_active >= cutoff).all()
        target_ids.update({row[0] for row in ids})

    if not target_ids:
        raise HTTPException(status_code=400, detail='请至少选择一个推送目标')

    valid_ids = {
        row[0]
        for row in db.query(User.id).filter(User.id.in_(target_ids), User.role == UserRole.USER).all()
    }
    if not valid_ids:
        raise HTTPException(status_code=400, detail='没有可推送的有效用户')

    for uid in valid_ids:
        db.add(Notification(
            user_id=uid,
            type=payload.type,
            title=payload.title,
            description=payload.description or None,
            related_task_id=payload.related_task_id,
            related_report_id=payload.related_report_id,
            related_user_id=payload.related_user_id,
            dismiss_type=payload.dismiss_type,
            is_read=False,
        ))

    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action='push_notification',
            target_type='notification',
            target_id='batch',
            detail=f'sent={len(valid_ids)}, type={payload.type}',
        )
    )
    db.commit()
    return AdminPushNotificationOut(sent_count=len(valid_ids), target_user_ids=sorted(valid_ids))


@router.get('/admin/notifications/sent', response_model=AdminSentNotificationListResponse)
def admin_list_sent_notifications(
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminSentNotificationListResponse:
    rows = (
        db.query(
            Notification.title,
            Notification.description,
            Notification.type,
            Notification.dismiss_type,
            func.count().label('remaining_count'),
            func.sum(case((Notification.is_read.is_(True), 1), else_=0)).label('read_count'),
            func.min(Notification.created_at).label('sent_at'),
        )
        .filter(Notification.type.in_(['admin_notice', 'admin_warning', 'admin_success', 'admin_info', 'admin_announcement']))
        .group_by(Notification.title, Notification.description, Notification.type, Notification.dismiss_type)
        .order_by(func.min(Notification.created_at).desc())
        .limit(30)
        .all()
    )
    items = [
        AdminSentNotificationItem(
            title=r.title,
            description=r.description,
            type=r.type,
            dismiss_type=r.dismiss_type,
            remaining_count=int(r.remaining_count),
            read_count=int(r.read_count or 0),
            sent_at=r.sent_at,
        )
        for r in rows
    ]
    return AdminSentNotificationListResponse(items=items)


@router.delete('/admin/notifications/sent')
def admin_delete_sent_notification(
    title: str = Query(...),
    type: str = Query(...),
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    count = db.query(Notification).filter(
        Notification.title == title,
        Notification.type == type,
    ).delete()
    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action='delete_notification_batch',
            target_type='notification',
            target_id='batch',
            detail=f'deleted={count}, title={title}',
        )
    )
    db.commit()
    return {'message': 'ok', 'deleted_count': count}


@router.get('/admin/action-logs', response_model=AdminActionLogListResponse)
def admin_list_action_logs(
    q: str | None = Query(default=None),
    action: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminActionLogListResponse:
    query = db.query(AdminActionLog)
    if action and action.strip():
        query = query.filter(AdminActionLog.action == action.strip())
    if q and q.strip():
        like = f'%{q.strip()}%'
        query = query.filter(
            or_(
                AdminActionLog.action.like(like),
                AdminActionLog.target_type.like(like),
                AdminActionLog.target_id.like(like),
                AdminActionLog.detail.like(like),
            )
        )
    total = query.count()
    rows = (
        query.order_by(desc(AdminActionLog.created_at), desc(AdminActionLog.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AdminActionLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            AdminActionLogItem(
                id=r.id,
                admin_identifier=r.admin_identifier,
                action=r.action,
                target_type=r.target_type,
                target_id=r.target_id,
                detail=r.detail,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )


@router.get('/admin/dashboard')
def admin_dashboard(
    days: int = Query(default=7, ge=3, le=30),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users_24h = db.query(func.count(User.id)).filter(User.last_active >= day_ago).scalar() or 0
    new_users_7d = db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar() or 0
    active_workers = db.query(func.count(WorkerProfile.id)).filter(WorkerProfile.enabled.is_(True)).scalar() or 0

    total_tasks = db.query(func.count(Task.id)).scalar() or 0
    open_tasks = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.OPEN).scalar() or 0
    in_progress_tasks = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.IN_PROGRESS).scalar() or 0
    under_review_tasks = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.UNDER_REVIEW).scalar() or 0
    completed_tasks = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.COMPLETED).scalar() or 0
    canceled_tasks = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.CANCELED).scalar() or 0
    overdue_open_tasks = (
        db.query(func.count(Task.id))
        .filter(
            Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_PROGRESS, TaskStatus.UNDER_REVIEW]),
            Task.deadline.isnot(None),
            Task.deadline < now,
        )
        .scalar()
        or 0
    )
    pinned_tasks = db.query(func.count(Task.id)).filter(Task.is_pinned.is_(True)).scalar() or 0
    urgent_tasks = db.query(func.count(Task.id)).filter(Task.is_urgent.is_(True)).scalar() or 0
    avg_task_price = db.query(func.avg(Task.price)).scalar() or 0

    pending_reports = db.query(func.count(Report.id)).filter(Report.status == ReportStatus.PENDING).scalar() or 0
    approved_reports_7d = (
        db.query(func.count(Report.id))
        .filter(Report.status == ReportStatus.APPROVED, Report.reviewed_at >= week_ago)
        .scalar()
        or 0
    )
    rejected_reports_7d = (
        db.query(func.count(Report.id))
        .filter(Report.status == ReportStatus.REJECTED, Report.reviewed_at >= week_ago)
        .scalar()
        or 0
    )

    chat_messages_24h = db.query(func.count(ChatMessage.id)).filter(ChatMessage.created_at >= day_ago).scalar() or 0
    registration_enabled = get_registration_enabled(db)

    report_received_map = dict(
        db.query(Report.reported_user_id, func.count(Report.id))
        .filter(Report.type == ReportType.REPORT, Report.reported_user_id.isnot(None))
        .group_by(Report.reported_user_id)
        .all()
    )
    risky_candidates = db.query(User).filter(User.role == UserRole.USER).order_by(desc(User.ban_count), desc(User.blocked_by_count)).limit(30).all()
    risk_users: list[AdminRiskUser] = []
    for u in risky_candidates:
        risk_users.append(AdminRiskUser(
            user_id=u.id,
            display_name=display_name(u),
            ban_count=u.ban_count or 0,
            blocked_by_count=u.blocked_by_count or 0,
            report_received_count=report_received_map.get(u.id, 0),
        ))
    risk_users.sort(
        key=lambda x: ((x.ban_count * 10) + (x.blocked_by_count * 2) + (x.report_received_count * 4)),
        reverse=True,
    )

    trends: list[AdminTrendPoint] = []
    for i in range(days - 1, -1, -1):
        day_start = datetime(now.year, now.month, now.day) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        trends.append(AdminTrendPoint(
            date=day_start.strftime('%m-%d'),
            new_users=(
                db.query(func.count(User.id))
                .filter(User.created_at >= day_start, User.created_at < day_end)
                .scalar()
                or 0
            ),
            new_tasks=(
                db.query(func.count(Task.id))
                .filter(Task.created_at >= day_start, Task.created_at < day_end)
                .scalar()
                or 0
            ),
            new_reports=(
                db.query(func.count(Report.id))
                .filter(Report.created_at >= day_start, Report.created_at < day_end)
                .scalar()
                or 0
            ),
            new_messages=(
                db.query(func.count(ChatMessage.id))
                .filter(ChatMessage.created_at >= day_start, ChatMessage.created_at < day_end)
                .scalar()
                or 0
            ),
        ))

    return {
        'total_users': total_users,
        'active_users_24h': active_users_24h,
        'new_users_7d': new_users_7d,
        'active_workers': active_workers,
        'total_tasks': total_tasks,
        'open_tasks': open_tasks,
        'in_progress_tasks': in_progress_tasks,
        'under_review_tasks': under_review_tasks,
        'completed_tasks': completed_tasks,
        'canceled_tasks': canceled_tasks,
        'overdue_open_tasks': overdue_open_tasks,
        'pinned_tasks': pinned_tasks,
        'urgent_tasks': urgent_tasks,
        'avg_task_price': round(float(avg_task_price), 2) if avg_task_price else 0,
        'pending_reports': pending_reports,
        'approved_reports_7d': approved_reports_7d,
        'rejected_reports_7d': rejected_reports_7d,
        'chat_messages_24h': chat_messages_24h,
        'completion_rate': round((completed_tasks / total_tasks), 4) if total_tasks else 0,
        'registration_enabled': registration_enabled,
        'trends': [t.model_dump() for t in trends],
        'top_risk_users': [u.model_dump() for u in risk_users[:5]],
    }


@router.get('/admin/registration-setting', response_model=RegistrationSettingOut)
def admin_get_registration_setting(
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RegistrationSettingOut:
    return RegistrationSettingOut(registration_enabled=get_registration_enabled(db))


@router.put('/admin/registration-setting', response_model=RegistrationSettingOut)
def admin_update_registration_setting(
    payload: RegistrationSettingUpdate,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RegistrationSettingOut:
    enabled = set_registration_enabled(db, payload.registration_enabled)
    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action='registration_toggle',
            target_type='platform_setting',
            target_id='registration_enabled',
            detail=str(enabled),
        )
    )
    db.commit()
    return RegistrationSettingOut(registration_enabled=enabled)
