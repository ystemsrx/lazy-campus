#!/usr/bin/env bash
set -euo pipefail

# =========================
#  LaZy Campus 管理脚本（dist 静态托管版）
#  用法：
#    ./manage.sh start
#    ./manage.sh stop
#    ./manage.sh restart
#    ./manage.sh status
#    ./manage.sh nginx        # 生成并启用 nginx 站点（HTTP），需 root/sudo
# =========================

# ── 基础路径 ────────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
FRONTEND_DIST="$FRONTEND_DIR/dist"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$PROJECT_DIR/.pids"

# ── 加载部署层 .env（如果存在）──────────────────────────────────────────────
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi

# ── 域名 & 端口配置（按需修改）──────────────────────────────────────────────
API_DOMAIN="${API_DOMAIN:-api.example.com}"
LINK_DOMAIN="${LINK_DOMAIN:-link.example.com}"

# 后端只监听本地，由 Nginx 对外
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# 后端启动参数
BACKEND_MODULE="${BACKEND_MODULE:-app.main:app}"
BACKEND_WORKERS="${BACKEND_WORKERS:-1}"   # 小机子建议 1；需要可改 2/4

# ── 颜色输出 ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*" >&2; }
success() { echo -e "${GREEN}[OK]${NC}    $*" >&2; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" >&2; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || error "缺少命令：$1"; }

is_port_listening() {
  local port="$1"
  ss -tln 2>/dev/null | awk '{print $4}' | grep -E "(^|:)${port}$" >/dev/null 2>&1 && return 0
  return 1
}

read_pids() {
  [ -f "$PID_FILE" ] || return 1
  # shellcheck disable=SC1090
  source "$PID_FILE"
  return 0
}

write_pids() {
  local bpid="$1"
  # 兼容旧版本：仍写 FRONTEND_PID 为空，避免老 stop/status 报错
  cat > "$PID_FILE" <<EOF
BACKEND_PID=$bpid
FRONTEND_PID=
EOF
}

kill_pid_gracefully() {
  local pid="$1" name="$2"
  if [ -z "${pid:-}" ]; then
    warn "$name PID 为空，跳过。"
    return 0
  fi
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    warn "$name（PID $pid）已不在运行。"
    return 0
  fi

  info "停止 $name（PID $pid）..."
  kill -TERM "$pid" >/dev/null 2>&1 || true

  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      success "$name 已停止。"
      return 0
    fi
    sleep 0.5
  done

  warn "$name 未在 10 秒内退出，强制杀掉（KILL）。"
  kill -KILL "$pid" >/dev/null 2>&1 || true
  success "$name 已强制停止。"
}

ensure_dirs() {
  [ -d "$BACKEND_DIR" ] || error "找不到目录：$BACKEND_DIR"
  [ -d "$FRONTEND_DIR" ] || error "找不到目录：$FRONTEND_DIR"
  mkdir -p "$LOG_DIR"
}

ensure_backend_env() {
  need_cmd ss
  local pybin
  pybin="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
  [ -n "$pybin" ] || error "未找到 python3 / python，请先安装 Python 3.9+。"

  local ver
  ver="$("$pybin" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")"
  info "[后端] 使用 Python $ver（$pybin）"

  local venv="$BACKEND_DIR/.venv"
  if [ ! -d "$venv" ]; then
    info "[后端] 创建虚拟环境：$venv"
    "$pybin" -m venv "$venv"
    success "[后端] 虚拟环境已创建"
  else
    info "[后端] 虚拟环境已存在，跳过创建"
  fi

  local vpy="$venv/bin/python" vpip="$venv/bin/pip"
  [ -f "$vpy" ] || vpy="$venv/Scripts/python"
  [ -f "$vpip" ] || vpip="$venv/Scripts/pip"
  [ -f "$vpy" ] || error "[后端] 找不到 venv python：$vpy"
  [ -f "$vpip" ] || error "[后端] 找不到 venv pip：$vpip"

  export VENV_PYTHON="$vpy"
  export VENV_PIP="$vpip"

  [ -f "$BACKEND_DIR/requirements.txt" ] || error "[后端] 找不到 requirements.txt：$BACKEND_DIR/requirements.txt"
  info "[后端] 安装/更新依赖（requirements.txt）..."
  "$VENV_PIP" install --upgrade pip -q
  "$VENV_PIP" install -r "$BACKEND_DIR/requirements.txt" -q
  success "[后端] 依赖安装完成"
}

ensure_frontend_build() {
  need_cmd node
  need_cmd npm
  info "[前端] $(node -v) / npm $(npm -v)"

  if [ -f "$FRONTEND_DIR/package-lock.json" ]; then
    info "[前端] 检测到 package-lock.json，使用 npm ci"
    npm ci --prefix "$FRONTEND_DIR" --silent
  else
    info "[前端] 未检测到 package-lock.json，使用 npm install"
    npm install --prefix "$FRONTEND_DIR" --silent
  fi
  success "[前端] 依赖安装完成"

  info "[前端] 生产构建（vite build）..."
  npm run build --prefix "$FRONTEND_DIR"
  success "[前端] 构建完成：$FRONTEND_DIST"

  [ -f "$FRONTEND_DIST/index.html" ] || error "[前端] dist/index.html 不存在，构建可能失败。请检查构建输出。"
}

start_backend() {
  if is_port_listening "$BACKEND_PORT"; then
    error "[后端] 端口 ${BACKEND_PORT} 已在监听，可能已有进程占用。"
  fi

  local third_party_url=""
  if [ -f "$BACKEND_DIR/.env" ]; then
    third_party_url="$(grep -E '^THIRD_PARTY_AUTH_URL=' "$BACKEND_DIR/.env" | cut -d'=' -f2- | tr -d '[:space:]' || true)"
    info "[认证] THIRD_PARTY_AUTH_URL = ${third_party_url:-（未设置）}"
  fi

  info "[后端] 启动 FastAPI：${BACKEND_MODULE} @ ${BACKEND_HOST}:${BACKEND_PORT}"
  nohup bash -c "cd \"$BACKEND_DIR\" && exec \"$VENV_PYTHON\" -m uvicorn \"$BACKEND_MODULE\" \
    --host \"$BACKEND_HOST\" \
    --port \"$BACKEND_PORT\" \
    --workers \"$BACKEND_WORKERS\" \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    " > "$LOG_DIR/backend.log" 2>&1 &

  local pid=$!
  sleep 0.2
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    error "[后端] 启动失败，请查看日志：$LOG_DIR/backend.log"
  fi
  success "[后端] 已启动（PID $pid），日志：$LOG_DIR/backend.log"
  echo "$pid"
}

cmd_start() {
  ensure_dirs

  if [ -f "$PID_FILE" ]; then
    warn "检测到 $PID_FILE，可能已启动过。你可以先 ./manage.sh status 或 ./manage.sh stop"
    exit 1
  fi

  info "══════════════════════════════════════════"
  info "      LaZy Campus 启动（dist 静态托管）     "
  info "══════════════════════════════════════════"

  ensure_backend_env
  ensure_frontend_build

  local bpid
  bpid="$(start_backend)"
  write_pids "$bpid"

  echo ""
  success "服务已启动 ✓"
  echo -e "  ${CYAN}后端(内网)${NC}   http://${BACKEND_HOST}:${BACKEND_PORT}"
  echo -e "  ${CYAN}API 文档${NC}     http://${BACKEND_HOST}:${BACKEND_PORT}/docs"
  echo -e "  ${CYAN}前端(dist)${NC}   ${FRONTEND_DIST}"
  echo ""
  echo -e "  ${CYAN}域名（需 Nginx）${NC}"
  echo -e "    https://${API_DOMAIN}   -> ${BACKEND_HOST}:${BACKEND_PORT}"
  echo -e "    https://${LINK_DOMAIN}  -> (nginx 静态托管 dist)"
  echo ""
  echo -e "  日志目录：${LOG_DIR}"
  echo -e "  停止服务：${YELLOW}./manage.sh stop${NC}"
  echo ""
}

cmd_stop() {
  if ! read_pids; then
    warn "未找到 $PID_FILE，可能未启动。"
    exit 0
  fi

  # 兼容旧字段：如果 FRONTEND_PID 存在也会尝试停；新版本为空会跳过
  kill_pid_gracefully "${FRONTEND_PID:-}" "前端(旧)"
  kill_pid_gracefully "${BACKEND_PID:-}" "后端"

  rm -f "$PID_FILE"
  success "已清理 PID 文件：$PID_FILE"
}

cmd_status() {
  echo -e "${CYAN}══════════════════════════════════════════${NC}"
  echo -e "${CYAN}                服务状态                  ${NC}"
  echo -e "${CYAN}══════════════════════════════════════════${NC}"

  if read_pids && [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo -e "${GREEN}[RUN]${NC} 后端 PID=$BACKEND_PID  ${BACKEND_HOST}:${BACKEND_PORT}"
  else
    echo -e "${RED}[DOWN]${NC} 后端（未运行或 PID 文件缺失）"
  fi

  if [ -f "$FRONTEND_DIST/index.html" ]; then
    echo -e "${GREEN}[OK]${NC}  前端 dist 存在：$FRONTEND_DIST"
  else
    echo -e "${YELLOW}[WARN]${NC} 前端 dist 不存在：$FRONTEND_DIST（请 ./manage.sh start 或手动 npm run build）"
  fi

  echo ""
  echo -e "日志：$LOG_DIR/backend.log"
}

cmd_restart() {
  cmd_stop || true
  cmd_start
}

# ── Nginx 配置生成（HTTP）────────────────────────────────────────────────────
nginx_write_site() {
  local name="$1" content="$2"
  local avail="/etc/nginx/sites-available/$name"
  local enabled="/etc/nginx/sites-enabled/$name"

  echo "$content" > "$avail"
  [ -L "$enabled" ] || ln -s "$avail" "$enabled"
}

cmd_nginx() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    need_cmd sudo
    exec sudo -E bash "$0" nginx
  fi

  need_cmd nginx

  info "[nginx] 写入站点配置（HTTP）：$API_DOMAIN / $LINK_DOMAIN"
  info "[nginx] 前端将静态托管：$FRONTEND_DIST"

  # API 站点：反代到 127.0.0.1:8000
  nginx_write_site "$API_DOMAIN" "
server {
    listen 80;
    server_name $API_DOMAIN;

    location / {
        proxy_pass http://$BACKEND_HOST:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
"

  # LINK 站点：直接托管 dist（SPA fallback）
  nginx_write_site "$LINK_DOMAIN" "
server {
    listen 80;
    server_name $LINK_DOMAIN;

    root $FRONTEND_DIST;
    index index.html;

    # 静态资源缓存（可选，但常用）
    location ~* \\\\.(?:css|js|mjs|map|png|jpg|jpeg|gif|svg|ico|webp|woff2?|ttf|eot)$ {
        try_files \$uri =404;
        expires 7d;
        add_header Cache-Control \"public, max-age=604800\" always;
    }

    # SPA 路由：不存在的路径回退到 index.html
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
"

  # 去掉默认站点（可选，但推荐，避免冲突）
  if [ -L /etc/nginx/sites-enabled/default ]; then
    warn "[nginx] 发现默认站点 /etc/nginx/sites-enabled/default，已移除（避免抢 default_server）"
    rm -f /etc/nginx/sites-enabled/default
  fi

  nginx -t
  systemctl reload nginx 2>/dev/null || nginx -s reload
  success "[nginx] 配置已生效（HTTP）"

  echo ""
  echo "下一步（HTTPS）："
  echo "  apt install certbot python3-certbot-nginx -y"
  echo "  certbot --nginx -d $API_DOMAIN -d $LINK_DOMAIN"
  echo ""
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    nginx)   cmd_nginx ;;
    *)
      cat <<EOF
用法：
  ./manage.sh start
  ./manage.sh stop
  ./manage.sh restart
  ./manage.sh status
  ./manage.sh nginx      # 生成并启用 nginx 站点（HTTP），需 root/sudo

可通过环境变量覆盖：
  API_DOMAIN / LINK_DOMAIN
  BACKEND_HOST / BACKEND_PORT
  BACKEND_MODULE / BACKEND_WORKERS

例子：
  API_DOMAIN=api.example.com LINK_DOMAIN=link.example.com ./manage.sh nginx
EOF
      exit 1
      ;;
  esac
}

main "$@"