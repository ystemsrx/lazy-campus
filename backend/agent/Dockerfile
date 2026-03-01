FROM python:3.13-slim-bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    LANG=zh_CN.UTF-8 \
    LC_ALL=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    PYTHONIOENCODING=utf-8 \
    PATH="/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib \
    MATPLOTLIBRC=/etc/matplotlib \
    NODE_PATH=/usr/local/share/pnpm/global/node_modules

# ============================================================
# 1) APT 源 + 基础工具 + 中文完整支持(locale/tz/fonts) + cloudflared
#    + pandoc(无LaTeX) + poppler
# ============================================================
RUN set -eux; \
    rm -f /etc/apt/sources.list; \
    rm -f /etc/apt/sources.list.d/*.list || true; \
    rm -f /etc/apt/sources.list.d/*.sources || true; \
    \
    mkdir -p /etc/apt/sources.list.d; \
    { \
      printf '%s\n' \
'Types: deb' \
'URIs: https://mirrors.tuna.tsinghua.edu.cn/debian' \
'Suites: bookworm bookworm-updates bookworm-backports' \
'Components: main contrib non-free non-free-firmware' \
'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
'' \
'Types: deb' \
'URIs: https://mirrors.tuna.tsinghua.edu.cn/debian-security' \
'Suites: bookworm-security' \
'Components: main contrib non-free non-free-firmware' \
'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg'; \
    } > /etc/apt/sources.list.d/debian.sources; \
    sed -i 's/\r$//' /etc/apt/sources.list.d/debian.sources; \
    \
    apt-get update; \
    \
    apt-get install -y --no-install-recommends \
      ca-certificates curl wget \
      git openssh-client \
      sudo \
      jq unzip zip xz-utils \
      bc file dnsutils \
      tini \
      build-essential cmake pkg-config \
      libffi-dev libssl-dev \
      zlib1g-dev \
      \
      # 中文完整支持：时区 + locale
      tzdata locales \
      \
      # 字体/中文支持（系统/Matplotlib）
      fontconfig \
      fonts-noto-cjk \
      fonts-wqy-zenhei \
      fonts-wqy-microhei \
      fonts-dejavu-core \
      \
      # pandoc（不装 LaTeX：配合 --no-install-recommends）
      pandoc \
      \
      # pdf2image 依赖（pdftoppm/pdftocairo）
      poppler-utils \
    ; \
    \
    # 配置时区
    ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime; \
    echo "${TZ}" > /etc/timezone; \
    \
    # 生成 zh_CN.UTF-8 locale
    sed -i -E 's/^#\s*(zh_CN\.UTF-8\s+UTF-8)/\1/' /etc/locale.gen; \
    locale-gen zh_CN.UTF-8; \
    update-locale LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 LANGUAGE=zh_CN:zh; \
    \
    # cloudflared repo + install
    mkdir -p --mode=0755 /usr/share/keyrings; \
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
      | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null; \
    printf '%s\n' \
'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared bookworm main' \
      > /etc/apt/sources.list.d/cloudflared.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends cloudflared; \
    cloudflared --version; \
    \
    # matplotlib 缓存目录（给非 root 用户写缓存用）
    mkdir -p /tmp/matplotlib; \
    chmod 1777 /tmp/matplotlib; \
    \
    # 清理 APT 缓存 + 无用文档/man/log
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb /var/cache/apt/archives/partial/* \
           /var/log/*.log /var/log/apt/* \
           /usr/share/doc/* /usr/share/man/* /usr/share/info/* \
           /usr/share/lintian/* /usr/share/linda/*

# ============================================================
# 1.5) 额外字体：从构建上下文 fonts/ 复制进镜像
#      - times.ttf (Times New Roman)
#      - Cambria*.ttf/ttc
#      - Consola*.ttf
#      - simhei.ttf / simkai.ttf / SimSun.ttf
# ============================================================
COPY fonts/ /usr/local/share/fonts/custom/

# ============================================================
# 1.6) 字体缓存 + matplotlib 全局默认字体 + pip 国内源
# ============================================================
RUN set -eux; \
    fc-cache -f; \
    mkdir -p /etc/matplotlib; \
    { \
      printf '%s\n' \
"font.family: sans-serif" \
"font.sans-serif: SimHei, SimSun, Noto Sans CJK SC, WenQuanYi Micro Hei, WenQuanYi Zen Hei, DejaVu Sans" \
"font.serif: Cambria, Times New Roman, SimSun, SimKai, DejaVu Serif" \
"font.monospace: Consolas, DejaVu Sans Mono" \
"axes.unicode_minus: False"; \
    } > /etc/matplotlib/matplotlibrc; \
    sed -i 's/\r$//' /etc/matplotlib/matplotlibrc; \
    \
    # pip 国内源
    { \
      printf '%s\n' \
'[global]' \
'index-url = https://pypi.tuna.tsinghua.edu.cn/simple' \
'trusted-host = pypi.tuna.tsinghua.edu.cn' \
'disable-pip-version-check = true'; \
    } > /etc/pip.conf; \
    sed -i 's/\r$//' /etc/pip.conf

# ============================================================
# 3) NVM + Node + pnpm + 全局工具（cfshare + agent-browser + pptxgenjs）
#    - 修复 require 找不到全局包：固定 NODE_PATH -> pnpm root -g
# ============================================================
ARG NODE_VERSION="20.20.0"
ARG NVM_INSTALL_VERSION="v0.40.4"

ENV NVM_DIR=/root/.nvm \
    NVM_NODEJS_ORG_MIRROR=https://cdn.npmmirror.com/binaries/node \
    NPM_CONFIG_REGISTRY=https://registry.npmmirror.com \
    PNPM_HOME=/usr/local/share/pnpm

RUN set -eux; \
    export METHOD=script PROFILE=/dev/null NVM_INSTALL_VERSION="${NVM_INSTALL_VERSION}"; \
    curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_INSTALL_VERSION}/install.sh" | bash; \
    . "${NVM_DIR}/nvm.sh"; \
    nvm install "${NODE_VERSION}"; \
    nvm alias default "${NODE_VERSION}"; \
    nvm use default; \
    \
    corepack enable; \
    corepack prepare pnpm@latest --activate; \
    \
    npm config set registry "${NPM_CONFIG_REGISTRY}"; \
    pnpm config set registry "${NPM_CONFIG_REGISTRY}"; \
    \
    # 全局 bin 固定到 /usr/local/bin
    mkdir -p "${PNPM_HOME}/global" /usr/local/bin; \
    pnpm config set global-dir "${PNPM_HOME}/global"; \
    pnpm config set global-bin-dir /usr/local/bin; \
    \
    # 允许 agent-browser 跑其脚本（避免 pnpm v10 安全限制导致功能缺失）
    pnpm --allow-build=agent-browser,puppeteer add -g \
      @ystemsrx/cfshare agent-browser pptxgenjs docx \
      @mermaid-js/mermaid-cli; \
    \
    # 建立稳定 NODE_PATH：/usr/local/share/pnpm/global/node_modules -> $(pnpm root -g)
    GLOBAL_NM="$(pnpm root -g)"; \
    mkdir -p /usr/local/share/pnpm/global; \
    ln -sfn "${GLOBAL_NM}" /usr/local/share/pnpm/global/node_modules; \
    \
    # 给非交互 shell 兜底：把 node/npm/pnpm/corepack 固定到 /usr/local/bin
    ln -sf "${NVM_DIR}/versions/node/v${NODE_VERSION}/bin/node" /usr/local/bin/node; \
    ln -sf "${NVM_DIR}/versions/node/v${NODE_VERSION}/bin/npm" /usr/local/bin/npm; \
    ln -sf "${NVM_DIR}/versions/node/v${NODE_VERSION}/bin/npx" /usr/local/bin/npx; \
    ln -sf "${NVM_DIR}/versions/node/v${NODE_VERSION}/bin/pnpm" /usr/local/bin/pnpm; \
    ln -sf "${NVM_DIR}/versions/node/v${NODE_VERSION}/bin/corepack" /usr/local/bin/corepack; \
    \
    node -v; npm -v; pnpm -v; \
    command -v cfshare; \
    command -v agent-browser; \
    command -v mmdc; \
    node -e "require('pptxgenjs'); console.log('pptxgenjs ok')"; \
    \
    # 清理 Node/npm/pnpm 缓存
    rm -rf "${NVM_DIR}/.cache" || true; \
    npm cache clean --force 2>/dev/null || true; \
    pnpm store prune 2>/dev/null || true; \
    rm -rf /root/.npm /root/.cache /root/.local/share/pnpm/store /tmp/*

# ============================================================
# 4) Python 常用包 + PDF/DICOM/PPT 相关包（无 heredoc）
# ============================================================
RUN set -eux; \
    python -m pip install --no-cache-dir -U pip setuptools wheel; \
    python -m pip install --no-cache-dir \
      numpy pandas scipy scikit-learn \
      matplotlib pillow \
      requests httpx aiohttp \
      beautifulsoup4 lxml \
      pyyaml python-dotenv \
      openpyxl \
      tqdm rich typer \
      pydantic \
      \
      pymupdf \
      pdf2image \
      pydicom \
      PyPDF2 \
      pypdf \
      python-pptx \
      "markitdown[all]"; \
    \
    # 字体自检（不影响构建成功与否）
    fc-list | grep -i "times new roman" | head -n 5 || true; \
    fc-list | grep -i "cambria" | head -n 5 || true; \
    fc-list | grep -i "consolas" | head -n 5 || true; \
    fc-list | grep -i "simhei" | head -n 5 || true; \
    fc-list | grep -i "simkai" | head -n 5 || true; \
    fc-list | grep -i "simsun" | head -n 5 || true; \
    python -c "from matplotlib import font_manager; n={f.name for f in font_manager.fontManager.ttflist}; \
print('Has SimSun:', 'SimSun' in n); \
print('Has SimHei:', 'SimHei' in n); \
print('Has SimKai:', 'SimKai' in n); \
print('Has Cambria:', 'Cambria' in n); \
print('Has Consolas:', 'Consolas' in n); \
print('Has Times New Roman:', 'Times New Roman' in n)"; \
    \
    # 卸载编译期依赖（运行时不需要）
    apt-get purge -y --auto-remove build-essential cmake pkg-config \
      libffi-dev libssl-dev zlib1g-dev; \
    \
    # 清理 pip 缓存 + __pycache__ + .pyc
    rm -rf /root/.cache/pip /root/.cache/matplotlib /tmp/*; \
    find /usr/local/lib/python* -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true; \
    find /usr/local/lib/python* -name '*.pyc' -delete 2>/dev/null || true

# ============================================================
# 5) 浏览器自动化：按你指定方式安装（官方下载源）
# ============================================================
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN set -eux; \
    apt-get update; \
    agent-browser install --with-deps; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb /var/cache/apt/archives/partial/* \
           /root/.cache /tmp/*

# ============================================================
# 6) 用户与 sudo 免密 + Kimi Code CLI + 最终清理
# ============================================================
RUN set -eux; \
    # 创建用户
    useradd -m -s /bin/bash agent; \
    echo "agent ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/agent; \
    chmod 0440 /etc/sudoers.d/agent; \
    \
    # 安装 Kimi Code CLI
    curl -LsSf https://code.kimi.com/install.sh | bash; \
    if [ -f /root/.local/bin/env ]; then . /root/.local/bin/env; fi; \
    command -v uv; \
    command -v uvx; \
    command -v kimi; \
    kimi --version; \
    uv tool install nano-pdf; \
    \
    # 最终清理：移除所有残留缓存，压缩镜像体积
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /var/tmp/*; \
    find / -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true; \
    find / -name '*.pyc' -delete 2>/dev/null || true; \
    rm -rf /root/.cache /root/.npm /root/.wget-hsts /tmp/*; \
    rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/info/* /usr/share/lintian/*

WORKDIR /workspace
ENTRYPOINT ["tini", "--"]
CMD ["/bin/bash"]