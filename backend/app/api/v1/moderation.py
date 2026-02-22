import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_admin, require_completed_user, require_user
from app.db.session import get_db
from app.models.enums import ReportStatus, ReportType, TaskStatus
from app.models.moderation import AdminActionLog, Blacklist, Report
from app.models.notification import Notification
from app.models.task import Task, TaskMessage, TaskReview
from app.models.user import User, WorkerProfile
from app.schemas.moderation import (
    AdminUserItem,
    AdminUserListResponse,
    AppealCreate,
    BanContextOut,
    BanContextRequest,
    BanRecord,
    BanUserRequest,
    BlacklistCreate,
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
        ru = users.get(r.reported_user_id) if r.reported_user_id else None
        if ru:
            out.reported_user_name = ru.name
            out.reported_user_nickname = ru.nickname
            out.reported_user_account = ru.account
            out.reported_user_ban_count = ru.ban_count or 0
        result.append(out)
    return result


@router.post('/reports', response_model=ReportOut)
def create_report(
    payload: ReportCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    if not payload.task_id:
        raise HTTPException(status_code=400, detail='举报必须关联任务')
    if not payload.reported_user_id:
        raise HTTPException(status_code=400, detail='举报必须指定被举报用户')
    if payload.reported_user_id == user.id:
        raise HTTPException(status_code=400, detail='不能举报自己')

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
    rows = db.query(Report).filter(Report.reporter_id == user.id).order_by(desc(Report.created_at)).all()
    return _enrich_reports(rows, db)


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
            BanRecord(
                source='report',
                reason=r.admin_notes or '违反社区规则。',
                created_at=r.reviewed_at or r.created_at,
            )
        )

    admin_bans = (
        db.query(AdminActionLog)
        .filter(
            AdminActionLog.action == 'ban_user',
            AdminActionLog.target_id == str(user.id),
        )
        .order_by(desc(AdminActionLog.created_at))
        .all()
    )
    for log in admin_bans:
        records.append(
            BanRecord(
                source='admin',
                reason=log.detail or '违反社区规则。',
                created_at=log.created_at,
            )
        )

    records.sort(key=lambda x: x.created_at, reverse=True)

    # ban_count is decremented on innocent unbans, so only show
    # the most recent ban_count records to exclude innocently reversed bans.
    ban_count = user.ban_count or 0
    records = records[:ban_count]

    return BanContextOut(
        ban_until=user.ban_until,
        ban_count=ban_count,
        records=records,
    )


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
    if payload.status == ReportStatus.APPROVED:
        if report.type == ReportType.REPORT and report.reported_user_id:
            reported_user = db.get(User, report.reported_user_id)
            if reported_user:
                days = _BAN_DAYS[min(reported_user.ban_count or 0, len(_BAN_DAYS) - 1)]
                reported_user.is_banned = True
                reported_user.ban_reason = payload.admin_notes or '违反社区规则。'
                now = datetime.now(timezone.utc)
                existing_until = reported_user.ban_until
                if existing_until and existing_until.replace(tzinfo=timezone.utc) > now:
                    base = existing_until.replace(tzinfo=timezone.utc)
                else:
                    base = now
                reported_user.ban_until = base + timedelta(days=days)
                reported_user.ban_count = (reported_user.ban_count or 0) + 1
                db.add(reported_user)
                ban_detail = f', banned user {report.reported_user_id} for {days}d'
        elif report.type == ReportType.APPEAL:
            appealer = db.get(User, report.reporter_id)
            if appealer and appealer.is_banned:
                appealer.is_banned = False
                appealer.ban_reason = None
                appealer.ban_until = None
                if (appealer.ban_count or 0) > 0:
                    appealer.ban_count = appealer.ban_count - 1
                db.add(appealer)
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
    db.add(Notification(
        user_id=report.reporter_id,
        type='report_reviewed',
        title=f'{type_label}{status_label}',
        description=f'你提交的{type_label}已被管理员审核，结果：{status_label}',
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

    if payload.banned:
        user.is_banned = True
        user.ban_reason = payload.reason or '违反社区规则。'
        user.ban_until = None
        user.ban_count = (user.ban_count or 0) + 1
        action = 'ban_user'
        detail = user.ban_reason
    else:
        user.is_banned = False
        user.ban_reason = None
        user.ban_until = None
        if payload.innocent and (user.ban_count or 0) > 0:
            user.ban_count = user.ban_count - 1
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
    return {'message': 'ok'}


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
