import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import require_completed_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix='/uploads', tags=['uploads'])

# ── 常量 ────────────────────────────────────────────────────────────────────
UPLOADS_ROOT = Path(__file__).resolve().parents[3] / 'uploads'
REPORTS_ROOT = UPLOADS_ROOT / 'reports'

MAX_FILE_SIZE = 8 * 1024 * 1024   # 8 MB
ALLOWED_MIME = {'image/webp', 'image/jpeg', 'image/png', 'image/gif'}
EXT_MAP = {
    'image/webp': '.webp',
    'image/jpeg': '.jpg',
    'image/png':  '.png',
    'image/gif':  '.gif',
}


@router.post('/images', response_model=dict)
async def upload_image(
    file: UploadFile,
    _user: User = Depends(require_completed_user),
) -> dict:
    """
    上传单张截图，返回对外扁平 URL（不暴露年月分区结构）。

    物理存储：uploads/reports/YYYY/MM/<uuid4hex><ext>
    对外 URL ：{backend}/api/v1/uploads/reports/<uuid4hex><ext>
    """
    content_type = file.content_type or ''
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f'不支持的文件类型：{content_type}，仅接受 JPEG / PNG / WebP / GIF',
        )

    data = await file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='文件过大，单张截图不得超过 8 MB')

    ext = EXT_MAP.get(content_type, '.bin')

    # 物理路径按年/月分区，但文件名全局唯一
    now = datetime.now(timezone.utc)
    dest_dir = REPORTS_ROOT / str(now.year) / f'{now.month:02d}'
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = f'{uuid.uuid4().hex}{ext}'
    (dest_dir / filename).write_bytes(data)

    # 对外只暴露文件名，不暴露年月路径
    url = f'{settings.backend_public_url}{settings.api_v1_prefix}/uploads/reports/{filename}'
    return {'url': url}


@router.get('/reports/{filename}')
async def serve_report_image(filename: str) -> FileResponse:
    """
    按文件名查找并下发举报截图。

    URL 中只有文件名，真实分区路径对调用方透明。
    使用 glob 在 reports/**/ 中定位文件（文件名含 UUID，冲突概率极低）。
    """
    # 基本安全：禁止路径穿越
    if '/' in filename or '\\' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail='非法文件名')

    matches = list(REPORTS_ROOT.glob(f'**/{filename}'))
    if not matches:
        raise HTTPException(status_code=404, detail='文件不存在')

    target = matches[0]
    media_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    return FileResponse(path=str(target), media_type=media_type)
