from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, require_admin, require_completed_user
from app.db.session import get_db
from app.models.enums import ReportStatus, TaskStatus
from app.models.moderation import AdminActionLog, Blacklist, Report
from app.models.task import Task
from app.models.user import User, WorkerProfile
from app.schemas.moderation import (
    BanUserRequest,
    BlacklistCreate,
    RegistrationSettingOut,
    RegistrationSettingUpdate,
    ReportCreate,
    ReportOut,
    ReportReview,
)
from app.services.auth_service import get_registration_enabled, set_registration_enabled

router = APIRouter(prefix='/moderation', tags=['moderation'])


@router.post('/reports', response_model=ReportOut)
def create_report(
    payload: ReportCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    if payload.task_id:
        task = db.get(Task, payload.task_id)
        if not task:
            raise HTTPException(status_code=404, detail='Task not found')
        task.status = TaskStatus.UNDER_REVIEW
        db.add(task)

    report = Report(
        type=payload.type,
        task_id=payload.task_id,
        reporter_id=user.id,
        reported_user_id=payload.reported_user_id,
        reason=payload.reason,
        evidence=payload.evidence,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get('/me/reports', response_model=list[ReportOut])
def list_my_reports(user: User = Depends(require_completed_user), db: Session = Depends(get_db)) -> list[ReportOut]:
    return db.query(Report).filter(Report.reporter_id == user.id).order_by(desc(Report.created_at)).all()


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
            'blocked_display_name': (users[row.blocked_user_id].nickname or users[row.blocked_user_id].name)
            if row.blocked_user_id in users
            else '未知用户',
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


@router.get('/admin/reports', response_model=list[ReportOut])
def admin_list_reports(
    status: ReportStatus | None = Query(default=None),
    _admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    query = db.query(Report)
    if status:
        query = query.filter(Report.status == status)
    return query.order_by(desc(Report.created_at)).all()


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

    db.add(report)
    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action='review_report',
            target_type='report',
            target_id=str(report_id),
            detail=f'status={payload.status.value}',
        )
    )
    db.commit()
    db.refresh(report)
    return report


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

    user.is_banned = payload.banned
    user.ban_reason = payload.reason if payload.banned else None
    db.add(user)
    db.add(
        AdminActionLog(
            admin_identifier=admin.admin_account or 'admin',
            action='ban_user' if payload.banned else 'unban_user',
            target_type='user',
            target_id=str(user_id),
            detail=payload.reason,
        )
    )
    db.commit()
    return {'message': 'ok'}


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
