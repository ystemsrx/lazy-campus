#!/usr/bin/env bash
set -euo pipefail

# ── 路径 ──────────────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$PROJECT_DIR/.pids"

# ── 端口配置（按需修改）────────────────────────────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=5173

# ── 颜色输出 ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 检查是否已在运行 ───────────────────────────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    warn "检测到 .pids 文件，服务可能已在运行。请先执行 ./stop.sh 再重新启动。"
    exit 1
fi

mkdir -p "$LOG_DIR"

echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}         LaZy Link 一键启动脚本           ${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""

# ────────────────────────────────────────────────────────────────────────────
# 1. 后端：虚拟环境 + 依赖安装 + 启动
# ────────────────────────────────────────────────────────────────────────────
info "[ 后端 ] 检查 Python 环境..."

PYTHON_BIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
[ -z "$PYTHON_BIN" ] && error "未找到 python3 / python，请先安装 Python 3.9+。"

PYTHON_VERSION=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "[ 后端 ] 使用 Python $PYTHON_VERSION（$PYTHON_BIN）"

VENV_DIR="$BACKEND_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    info "[ 后端 ] 创建虚拟环境..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    success "[ 后端 ] 虚拟环境已创建：$VENV_DIR"
else
    info "[ 后端 ] 虚拟环境已存在，跳过创建。"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
# Windows Git Bash / MSYS2 兼容
[ ! -f "$VENV_PYTHON" ] && VENV_PYTHON="$VENV_DIR/Scripts/python"
[ ! -f "$VENV_PIP"    ] && VENV_PIP="$VENV_DIR/Scripts/pip"

info "[ 后端 ] 安装/更新依赖（requirements.txt）..."
"$VENV_PIP" install --upgrade pip -q
"$VENV_PIP" install -r "$BACKEND_DIR/requirements.txt" -q
success "[ 后端 ] 依赖安装完成。"

# 从 backend/.env 读取第三方认证 URL 并输出（不启动模拟服务）
THIRD_PARTY_URL=""
BACKEND_ENV="$BACKEND_DIR/.env"
if [ -f "$BACKEND_ENV" ]; then
    THIRD_PARTY_URL=$(grep -E '^THIRD_PARTY_AUTH_URL=' "$BACKEND_ENV" | cut -d'=' -f2- | tr -d '[:space:]')
    info "[ 认证 ] THIRD_PARTY_AUTH_URL = ${THIRD_PARTY_URL:-（未设置）}"
fi

# 启动后端（生产模式，不带 --reload）
info "[ 后端 ] 启动 FastAPI（端口 $BACKEND_PORT）..."
(cd "$BACKEND_DIR" && nohup "$VENV_PYTHON" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    > "$LOG_DIR/backend.log" 2>&1) &
BACKEND_PID=$!
success "[ 后端 ] 已启动（PID $BACKEND_PID）"

# ────────────────────────────────────────────────────────────────────────────
# 2. 前端：依赖安装 + 构建 + 预览服务
# ────────────────────────────────────────────────────────────────────────────
info "[ 前端 ] 检查 Node.js / npm..."
command -v node >/dev/null 2>&1 || error "未找到 node，请先安装 Node.js 18+。"
command -v npm  >/dev/null 2>&1 || error "未找到 npm，请先安装 npm。"
info "[ 前端 ] $(node -v)  /  npm $(npm -v)"

info "[ 前端 ] 安装/更新 npm 依赖..."
npm install --prefix "$FRONTEND_DIR" --silent
success "[ 前端 ] npm 依赖安装完成。"

info "[ 前端 ] 执行生产构建（vue-tsc + vite build）..."
npm run build --prefix "$FRONTEND_DIR"
success "[ 前端 ] 构建完成，产物位于 frontend/dist。"

info "[ 前端 ] 启动静态预览服务（端口 $FRONTEND_PORT）..."
nohup "$FRONTEND_DIR/node_modules/.bin/vite" preview \
    --outDir dist \
    --host 0.0.0.0 \
    --port "$FRONTEND_PORT" \
    > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
success "[ 前端 ] 已启动（PID $FRONTEND_PID）"

# ────────────────────────────────────────────────────────────────────────────
# 3. 保存 PID 以供 stop.sh 使用
# ────────────────────────────────────────────────────────────────────────────
cat > "$PID_FILE" <<EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
EOF

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}          所有服务已成功启动 ✓             ${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}前端地址${NC}     http://0.0.0.0:${FRONTEND_PORT}"
echo -e "  ${CYAN}后端 API${NC}     http://0.0.0.0:${BACKEND_PORT}/api/v1"
echo -e "  ${CYAN}API 文档${NC}     http://0.0.0.0:${BACKEND_PORT}/docs"
echo -e "  ${CYAN}第三方认证${NC}   ${THIRD_PARTY_URL:-（见 backend/.env）}"
echo ""
echo -e "  日志目录：${LOG_DIR}"
echo -e "  停止服务：${YELLOW}./stop.sh${NC}"
echo ""
