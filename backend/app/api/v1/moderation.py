import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_admin, require_completed_user, require_user
from app.db.session import get_db
from app.models.enums import ReportStatus, ReportType, TaskStatus
from app.models.chat import ChatMessage
from app.models.moderation import AdminActionLog, Blacklist, Report
from app.models.notification import Notification
from app.models.task import Task, TaskMessage, TaskReview
from app.models.user import User, WorkerProfile
from app.schemas.moderation import (
    AdminUserItem,
    AdminUserListResponse,
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


def _enrich_reports(reports: list[Report], db: Session) -> list[ReportOut]:
    user_ids: set[int] = set()
    for r in reports:
        user_ids.add(r.reporter_id)
        if r.reported_user_id:
            user_ids.add(r.reported_user_id)
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    result: list[ReportOut] = []
    for r in reports:
        out = ReportOut.model_validate(r)
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
        # 任务举报：校验任务存在且举报者为参与者
        task = db.get(Task, payload.task_id)
        if not task:
            raise HTTPException(status_code=404, detail='任务不存在')
        if task.publisher_id != user.id and task.assignee_id != user.id:
            raise HTTPException(status_code=403, detail='只有任务参与者可以举报')
        if not task.assignee_id:
            raise HTTPException(status_code=400, detail='该任务尚无接单者，无法举报')

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
    query = db.query(Report)
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
    if task.assignee_id:
        user_ids.add(task.assignee_id)

    messages = (
        db.query(TaskMessage)
        .filter(TaskMessage.task_id == task_id)
        .order_by(TaskMessage.created_at)
        .all()
    )
    for m in messages:
        user_ids.add(m.sender_id)

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

    return TaskSnapshotOut(
        id=task.id,
        title=task.title,
        description=task.description,
        deadline=task.deadline,
        location=task.location,
        price=task.price,
        status=task.status.value,
        publisher_display_name=dn(task.publisher_id),
        assignee_display_name=dn(task.assignee_id) if task.assignee_id else None,
        created_at=task.created_at,
        messages=[
            TaskSnapshotMessage(
                sender_display_name=dn(m.sender_id),
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ],
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

    messages = (
        db.query(ChatMessage)
        .filter(
            or_(
                (ChatMessage.sender_id == user_a) & (ChatMessage.receiver_id == user_b),
                (ChatMessage.sender_id == user_b) & (ChatMessage.receiver_id == user_a),
            )
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
    page_size: int = Query(default=20, ge=1, le=20),
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
    items = query.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()
    return AdminUserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            AdminUserItem(
                id=u.id,
                account=u.account,
                name=u.name,
                nickname=u.nickname,
                display_name=display_name(u),
                avatar_url=u.avatar_url,
                role=u.role.value,
                is_banned=u.is_banned,
                ban_reason=u.ban_reason,
                ban_count=u.ban_count or 0,
                ban_until=u.ban_until,
                ban_publish=u.ban_publish or False,
                ban_accept=u.ban_accept or False,
                ban_contact=u.ban_contact or False,
                created_at=u.created_at,
            )
            for u in items
        ],
    )


@router.get('/admin/dashboard')
def admin_dashboard(_admin: AuthContext = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_workers = db.query(func.count(WorkerProfile.id)).filter(WorkerProfile.enabled.is_(True)).scalar() or 0
    total_tasks = db.query(func.count(Task.id)).scalar() or 0
    completed_tasks = db.query(func.count(Task.id)).filter(Task.status == TaskStatus.COMPLETED).scalar() or 0
    pending_reports = db.query(func.count(Report.id)).filter(Report.status == ReportStatus.PENDING).scalar() or 0
    registration_enabled = get_registration_enabled(db)

    return {
        'total_users': total_users,
        'active_workers': active_workers,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_reports': pending_reports,
        'completion_rate': round((completed_tasks / total_tasks), 4) if total_tasks else 0,
        'registration_enabled': registration_enabled,
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
