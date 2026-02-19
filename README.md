# 校园任务平台（FastAPI + SQLite + Vue3 + Vite）

本项目实现了你提出的核心需求：
- 登录：本地优先校验，失败后回退第三方接口并自动回写数据库。
- 账号策略：首次登录强制补全邮箱/性别/昵称；昵称优先对外展示。
- 密码存储：`PASSWORD_ENCRYPTION` 可切换明文/哈希；开启加密后支持旧明文自动迁移。
- 注册开关：登录页支持用户注册入口，管理员可在后台随时开启/关闭注册。
- 双向平台：既可“接委托”，也可“找委托人（接单者）”。
- 核心闭环：发布 -> 接取 -> 沟通 -> 完成 -> 互评 -> 举报/申诉 -> 管理审核。
- 管理端：举报审核、用户封禁、类目管理、看板统计。
- 隐私与权限：联系方式按规则可见、任务资料默认仅参与者可见、站内消息反骚扰限频。

## 目录结构

```text
backend/
  app/
    api/v1/         # 路由层
    core/           # 配置/安全
    db/             # 数据库连接与初始化
    models/         # SQLAlchemy 模型
    schemas/        # Pydantic DTO
    services/       # 业务服务（登录）
    utils/          # 通用工具
  scripts/mock_auth_service.py
  requirements.txt

frontend/
  src/
    api/            # API 封装
    stores/         # Pinia 状态管理
    router/         # 路由守卫（含首次补全逻辑）
    views/          # 页面
```

## 后端关键设计

1. 登录流程（`backend/app/services/auth_service.py`）
- 命中管理员 env 账号：直接管理员登录。
- 普通用户：
  - 先查本地账号并校验密码。
  - 本地失败则调用第三方接口。
  - 第三方成功后自动创建/更新本地用户与密码。

2. 密码加密策略
- `PASSWORD_ENCRYPTION=true`：PBKDF2-SHA256 哈希存储。
- `PASSWORD_ENCRYPTION=false`：明文存储（开发调试）。
- 自动迁移：用户本地登录成功且发现旧数据是明文时，自动迁移为哈希。

3. 权限与隐私
- JWT 鉴权，区分 `user/admin`。
- 首次补全信息前，仅允许补全相关操作。
- 联系方式：`after_accept` 仅接取后可见；`internal_only` 永不展示。
- 附件资料：仅任务参与者可读写。
- 聊天：仅参与者可聊，含黑名单拦截与消息发送频率限制（3秒）。

4. 排序权重
- 任务/接单者列表按评分、评价数、被拉黑数综合排序，满足信誉沉淀要求。

## 前端页面

- `LoginView.vue`：账号登录。
- `CompleteProfileView.vue`：首次必填资料补全。
- `HomeView.vue`：
  - 顶部“接委托/找委托人”模式切换。
  - 发布委托、接单者 profile 管理。
  - 任务接取/确认完成、站内聊天、双向互评、举报申诉。
- `AdminView.vue`：管理员看板、举报审核、封禁用户。
  - 额外支持“用户注册开关”在线配置。

## 运行步骤

1. 启动第三方认证（本地模拟，可选）
```bash
cd backend
python -m uvicorn scripts.mock_auth_service:app --port 9000 --reload
```

2. 启动后端
```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

3. 启动前端
```bash
cd frontend
npm install
npm run dev
```

默认前端访问 `http://localhost:5173`，后端访问 `http://127.0.0.1:8000`。

## 生产环境建议（下一步）

1. 引入 Alembic 管理数据库迁移（替换当前轻量启动迁移）。
2. 接入 Redis 实现更严格的限流、会话黑名单与异步队列。
3. 文件附件改为对象存储（S3/OSS），并加签访问控制。
4. 增加自动化测试（服务层单测 + API 集成测试 + E2E）。
5. 增加审计追踪、监控告警与日志聚合（OpenTelemetry + Prometheus + Loki）。
