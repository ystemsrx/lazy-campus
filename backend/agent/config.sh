#!/usr/bin/env bash
set -euo pipefail

# Kimi CLI runtime bootstrap.
# 可在这里注入代理运行时需要的环境变量（例如代理地址、模型参数等）。
# 实际敏感配置建议写入同目录的 .env（由 docker --env-file 注入）。

export KIMI_NON_INTERACTIVE=1

# Ensure common install locations are in PATH for non-interactive shells.
_append_path_once() {
  local dir="$1"
  if [ -d "$dir" ] && [[ ":$PATH:" != *":$dir:"* ]]; then
    PATH="${PATH}:$dir"
  fi
}

_append_path_once "/usr/local/bin"
_append_path_once "/usr/bin"
_append_path_once "/bin"
_append_path_once "/root/.local/bin"
_append_path_once "/root/.npm-global/bin"

for node_bin_dir in /root/.nvm/versions/node/*/bin; do
  _append_path_once "$node_bin_dir"
done

export PATH

# Allow overriding the CLI path, otherwise auto-discover.
if [ -n "${KIMI_CLI_BIN:-}" ] && [ -x "${KIMI_CLI_BIN}" ]; then
  export KIMI_CLI_BIN
elif command -v kimi >/dev/null 2>&1; then
  export KIMI_CLI_BIN="$(command -v kimi)"
elif command -v kimi-code >/dev/null 2>&1; then
  export KIMI_CLI_BIN="$(command -v kimi-code)"
else
  export KIMI_CLI_BIN=""
fi

if [ -z "${KIMI_CLI_BIN}" ]; then
  echo "Kimi CLI not found. Please install kimi in image or set KIMI_CLI_BIN." >&2
  return 1 2>/dev/null || exit 1
fi

KIMI_EFFECTIVE_API_KEY="${KIMI_CODE_API_KEY:-${KIMI_API_KEY:-}}"
if [ -z "${KIMI_EFFECTIVE_API_KEY}" ]; then
  echo "KIMI_CODE_API_KEY or KIMI_API_KEY is required." >&2
  return 1 2>/dev/null || exit 1
fi
if [ "${KIMI_EFFECTIVE_API_KEY}" = "please_set_me" ] || [ "${KIMI_EFFECTIVE_API_KEY}" = "your_kimi_api_key_here" ]; then
  echo "Kimi API key is placeholder. Please update backend/agent/.env." >&2
  return 1 2>/dev/null || exit 1
fi
export KIMI_EFFECTIVE_API_KEY

# ---- helpers: sanitize env values ----
_strip_wrapping_quotes() {
  # remove one pair of wrapping single/double quotes if present
  local s="$1"
  if [[ "$s" =~ ^\".*\"$ ]]; then s="${s:1:${#s}-2}"; fi
  if [[ "$s" =~ ^\'.*\'$ ]]; then s="${s:1:${#s}-2}"; fi
  printf '%s' "$s"
}

_to_toml_bool() {
  # normalize common truthy/falsey to TOML true/false
  local v="${1:-false}"
  v="$(_strip_wrapping_quotes "$v")"
  case "${v,,}" in
    true|1|yes|y|on)  printf 'true' ;;
    false|0|no|n|off|"") printf 'false' ;;
    *)
      echo "Invalid boolean value for TOML: '$v' (use true/false)" >&2
      return 1
      ;;
  esac
}

# ---- runtime params ----
KIMI_MODEL="$(_strip_wrapping_quotes "${KIMI_MODEL:-kimi-for-coding}")"
KIMI_BASE_URL="$(_strip_wrapping_quotes "${KIMI_BASE_URL:-https://api.kimi.com/coding/v1}")"
KIMI_SEARCH_URL="$(_strip_wrapping_quotes "${KIMI_SEARCH_URL:-${KIMI_BASE_URL}/search}")"
KIMI_FETCH_URL="$(_strip_wrapping_quotes "${KIMI_FETCH_URL:-${KIMI_BASE_URL}/fetch}")"
KIMI_DEFAULT_THINKING="$(_to_toml_bool "${KIMI_DEFAULT_THINKING:-false}")"
KIMI_DEFAULT_YOLO="$(_to_toml_bool "${KIMI_DEFAULT_YOLO:-true}")"

mkdir -p /root/.kimi

# Always rewrite config to keep runtime deterministic across sessions.
cat > /root/.kimi/config.toml <<EOF
default_model = "${KIMI_MODEL}"
default_thinking = ${KIMI_DEFAULT_THINKING}
default_yolo = ${KIMI_DEFAULT_YOLO}

[providers."kimi-code"]
type = "kimi"
base_url = "${KIMI_BASE_URL}"
api_key = "${KIMI_EFFECTIVE_API_KEY}"

# IMPORTANT:
# Model keys that contain '.' must be quoted in TOML, otherwise they become nested tables.
[models."${KIMI_MODEL}"]
provider = "kimi-code"
model = "${KIMI_MODEL}"
max_context_size = 262144

[loop_control]
max_steps_per_turn = 100
max_retries_per_step = 3
max_ralph_iterations = 0
reserved_context_size = 50000

[services.moonshot_search]
base_url = "${KIMI_SEARCH_URL}"
api_key = "${KIMI_EFFECTIVE_API_KEY}"
custom_headers = { "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Accept" = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Accept-Language" = "zh-CN,zh;q=0.9,en;q=0.8" }

[services.moonshot_fetch]
base_url = "${KIMI_FETCH_URL}"
api_key = "${KIMI_EFFECTIVE_API_KEY}"
custom_headers = { "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Accept" = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Accept-Language" = "zh-CN,zh;q=0.9,en;q=0.8" }
EOF