#!/usr/bin/env bash
set -euo pipefail

# ── 路径 ──────────────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_DIR/.pids"

# ── 颜色输出 ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }

echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}         LaZy Link 一键停止脚本           ${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""

if [ ! -f "$PID_FILE" ]; then
    warn "未找到 .pids 文件，服务可能未在运行或已被手动停止。"
    echo ""
    exit 0
fi

# ── 读取 PID ──────────────────────────────────────────────────────────────────
# shellcheck source=/dev/null
source "$PID_FILE"

# ── 停止单个进程（及其子进程）────────────────────────────────────────────────────
kill_group() {
    local name="$1"
    local pid="$2"

    if [ -z "${pid:-}" ]; then
        warn "[ $name ] PID 未记录，跳过。"
        return
    fi

    # 尝试终止进程组（nohup 下 uvicorn/vite 会产生子进程）
    if kill -0 "$pid" 2>/dev/null; then
        # 先发 SIGTERM，给进程机会优雅退出
        kill -TERM "$pid" 2>/dev/null || true

        # 等待最多 5 秒
        local waited=0
        while kill -0 "$pid" 2>/dev/null && [ "$waited" -lt 5 ]; do
            sleep 1
            waited=$((waited + 1))
        done

        # 如果仍然存活，强制 SIGKILL
        if kill -0 "$pid" 2>/dev/null; then
            kill -KILL "$pid" 2>/dev/null || true
            warn "[ $name ] 进程 $pid 未响应 SIGTERM，已强制终止（SIGKILL）。"
        else
            success "[ $name ] 已停止（PID $pid）"
        fi
    else
        warn "[ $name ] 进程 $pid 已不存在，跳过。"
    fi
}

kill_group "前端预览服务" "${FRONTEND_PID:-}"
kill_group "后端 FastAPI"  "${BACKEND_PID:-}"

# ── 清理 PID 文件 ─────────────────────────────────────────────────────────────
rm -f "$PID_FILE"

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}          所有服务已成功停止 ✓             ${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
