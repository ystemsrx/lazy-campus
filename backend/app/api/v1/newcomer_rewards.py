from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.newcomer_reward import NewcomerRewardLog, NewcomerRewardRule
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix='/admin/newcomer-rewards', tags=['newcomer-rewards'])


class RewardRuleOut(BaseModel):
    id: int
    reward_type: str
    reward_detail: str
    enabled: bool
    start_time: str | None
    end_time: str | None
    created_at: str
    updated_at: str


class RewardRuleListResponse(BaseModel):
    items: list[RewardRuleOut]
    total: int


class RewardRuleCreateRequest(BaseModel):
    reward_type: str = Field(..., max_length=32)
    reward_detail: str = Field(..., max_length=255)
    start_time: str | None = None
    end_time: str | None = None


class RewardRuleUpdateRequest(BaseModel):
    reward_type: str | None = Field(None, max_length=32)
    reward_detail: str | None = Field(None, max_length=255)
    enabled: bool | None = None
    start_time: str | None = None
    end_time: str | None = None


class RewardLogOut(BaseModel):
    id: int
    user_id: int
    user_display_name: str
    user_account: str
    rule_id: int
    reward_type: str
    reward_detail: str
    status: str
    fail_reason: str | None
    created_at: str


class RewardLogListResponse(BaseModel):
    items: list[RewardLogOut]
    total: int


class RewardManualGrantRequest(BaseModel):
    rule_id: int | None = Field(default=None, ge=1)
    reward_type: str | None = Field(default=None, max_length=32)
    reward_detail: str | None = Field(default=None, max_length=255)
    user_ids: list[int] = Field(..., min_length=1, max_length=200)


class RewardManualGrantResponse(BaseModel):
    requested_count: int
    processed_count: int
    success_count: int
    failed_count: int
    missing_user_ids: list[int]


def _dt_to_str(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _parse_dt(s: str | None) -> datetime | None:
    if not s or s.strip() == '':
        return None
    s = s.strip()
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=422, detail=f'Invalid datetime format: {s}')


def _rule_to_out(rule: NewcomerRewardRule) -> RewardRuleOut:
    return RewardRuleOut(
        id=rule.id,
        reward_type=rule.reward_type,
        reward_detail=rule.reward_detail,
        enabled=rule.enabled,
        start_time=_dt_to_str(rule.start_time),
        end_time=_dt_to_str(rule.end_time),
        created_at=_dt_to_str(rule.created_at) or '',
        updated_at=_dt_to_str(rule.updated_at) or '',
    )


def _normalize_reward_payload(reward_type: str, reward_detail: str) -> tuple[str, str]:
    normalized_type = reward_type.strip()
    normalized_detail = reward_detail.strip()
    if not normalized_type:
        raise HTTPException(status_code=422, detail='reward_type is required')
    if not normalized_detail:
        raise HTTPException(status_code=422, detail='reward_detail is required')
    if normalized_type != 'agent_usage':
        raise HTTPException(status_code=422, detail='Unsupported reward_type')
    try:
        amount = int(normalized_detail)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail='代理使用次数必须为正整数') from exc
    if amount <= 0:
        raise HTTPException(status_code=422, detail='代理使用次数必须为正整数')
    return normalized_type, str(amount)


def _ensure_manual_grant_rule(db: Session) -> NewcomerRewardRule:
    system_rule = (
        db.query(NewcomerRewardRule)
        .filter(NewcomerRewardRule.reward_type == 'manual_grant')
        .order_by(NewcomerRewardRule.id.asc())
        .first()
    )
    if system_rule:
        return system_rule
    system_rule = NewcomerRewardRule(
        reward_type='manual_grant',
        reward_detail='系统手动发放占位规则',
        enabled=False,
    )
    db.add(system_rule)
    db.flush()
    return system_rule


@router.get('/rules', response_model=RewardRuleListResponse)
def list_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> RewardRuleListResponse:
    total = (
        db.query(func.count(NewcomerRewardRule.id))
        .filter(NewcomerRewardRule.reward_type != 'manual_grant')
        .scalar()
        or 0
    )
    items = (
        db.query(NewcomerRewardRule)
        .filter(NewcomerRewardRule.reward_type != 'manual_grant')
        .order_by(desc(NewcomerRewardRule.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return RewardRuleListResponse(items=[_rule_to_out(r) for r in items], total=total)


@router.post('/rules', response_model=RewardRuleOut, status_code=201)
def create_rule(
    payload: RewardRuleCreateRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> RewardRuleOut:
    if payload.reward_type.strip() == 'manual_grant':
        raise HTTPException(status_code=400, detail='该奖励类型为系统保留类型')

    rule = NewcomerRewardRule(
        reward_type=payload.reward_type,
        reward_detail=payload.reward_detail,
        enabled=True,
        start_time=_parse_dt(payload.start_time),
        end_time=_parse_dt(payload.end_time),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_out(rule)


@router.put('/rules/{rule_id}', response_model=RewardRuleOut)
def update_rule(
    rule_id: int,
    payload: RewardRuleUpdateRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> RewardRuleOut:
    rule = db.get(NewcomerRewardRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail='Rule not found')
    if rule.reward_type == 'manual_grant':
        raise HTTPException(status_code=400, detail='系统保留规则不允许编辑')

    if payload.reward_type is not None:
        if payload.reward_type.strip() == 'manual_grant':
            raise HTTPException(status_code=400, detail='该奖励类型为系统保留类型')
        rule.reward_type = payload.reward_type
    if payload.reward_detail is not None:
        rule.reward_detail = payload.reward_detail
    if payload.enabled is not None:
        rule.enabled = payload.enabled
    if 'start_time' in (payload.model_fields_set or set()):
        rule.start_time = _parse_dt(payload.start_time)
    if 'end_time' in (payload.model_fields_set or set()):
        rule.end_time = _parse_dt(payload.end_time)

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_out(rule)


@router.delete('/rules/{rule_id}')
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> dict:
    rule = db.get(NewcomerRewardRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail='Rule not found')
    if rule.reward_type == 'manual_grant':
        raise HTTPException(status_code=400, detail='系统保留规则不允许删除')
    db.delete(rule)
    db.commit()
    return {'ok': True}


@router.patch('/rules/{rule_id}/toggle', response_model=RewardRuleOut)
def toggle_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> RewardRuleOut:
    rule = db.get(NewcomerRewardRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail='Rule not found')
    if rule.reward_type == 'manual_grant':
        raise HTTPException(status_code=400, detail='系统保留规则不允许切换')
    rule.enabled = not rule.enabled
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_out(rule)


@router.post('/grant', response_model=RewardManualGrantResponse)
def grant_reward_to_users(
    payload: RewardManualGrantRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> RewardManualGrantResponse:
    reward_type: str | None = None
    reward_detail: str | None = None
    source_rule: NewcomerRewardRule | None = None

    if payload.rule_id is not None:
        source_rule = db.get(NewcomerRewardRule, payload.rule_id)
        if not source_rule:
            raise HTTPException(status_code=404, detail='Rule not found')
        reward_type, reward_detail = _normalize_reward_payload(source_rule.reward_type, source_rule.reward_detail)
    else:
        if payload.reward_type is None or payload.reward_detail is None:
            raise HTTPException(status_code=422, detail='reward_type and reward_detail are required when rule_id is not provided')
        reward_type, reward_detail = _normalize_reward_payload(payload.reward_type, payload.reward_detail)
        source_rule = _ensure_manual_grant_rule(db)

    dedup_user_ids = list(dict.fromkeys(payload.user_ids))
    success_count = 0
    failed_count = 0
    processed_count = 0
    missing_user_ids: list[int] = []

    for user_id in dedup_user_ids:
        user = db.get(User, user_id)
        if not user:
            missing_user_ids.append(user_id)
            continue
        processed_count += 1

        status = 'success'
        fail_reason = None
        reward_text = f'{reward_type}: {reward_detail}'
        try:
            if reward_type == 'agent_usage':
                amount = int(reward_detail)
                user.agent_usage_remaining = (user.agent_usage_remaining or 0) + amount
                db.add(user)
                reward_text = f'代理使用次数 +{amount} 次'
            success_count += 1
            db.add(Notification(
                user_id=user.id,
                type='newcomer_reward',
                title='奖励已发放',
                description=f'管理员已为你发放奖励：{reward_text}',
                dismiss_type='read',
                is_read=False,
            ))
        except Exception as exc:  # noqa: BLE001
            status = 'failed'
            fail_reason = str(exc)
            failed_count += 1

        db.add(NewcomerRewardLog(
            user_id=user.id,
            rule_id=source_rule.id,
            reward_type=reward_type,
            reward_detail=reward_detail,
            status=status,
            fail_reason=fail_reason,
        ))

    db.commit()
    return RewardManualGrantResponse(
        requested_count=len(payload.user_ids),
        processed_count=processed_count,
        success_count=success_count,
        failed_count=failed_count,
        missing_user_ids=missing_user_ids,
    )


@router.get('/logs', response_model=RewardLogListResponse)
def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    reward_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias='status'),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> RewardLogListResponse:
    query = db.query(NewcomerRewardLog, User).outerjoin(User, NewcomerRewardLog.user_id == User.id)

    if reward_type:
        query = query.filter(NewcomerRewardLog.reward_type == reward_type)
    if status_filter:
        query = query.filter(NewcomerRewardLog.status == status_filter)
    if q:
        pattern = f'%{q}%'
        query = query.filter(
            (User.account.ilike(pattern)) | (User.name.ilike(pattern)) | (User.nickname.ilike(pattern))
        )

    total = query.count()
    rows = (
        query.order_by(desc(NewcomerRewardLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for log, user in rows:
        items.append(RewardLogOut(
            id=log.id,
            user_id=log.user_id,
            user_display_name=(user.nickname or user.name) if user else f'用户#{log.user_id}',
            user_account=user.account if user else '',
            rule_id=log.rule_id,
            reward_type=log.reward_type,
            reward_detail=log.reward_detail,
            status=log.status,
            fail_reason=log.fail_reason,
            created_at=_dt_to_str(log.created_at) or '',
        ))

    return RewardLogListResponse(items=items, total=total)
