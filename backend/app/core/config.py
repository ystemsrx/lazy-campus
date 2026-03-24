from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


def _replace_localhost_for_docker(url: str) -> str:
    normalized = (url or '').strip()
    if not normalized:
        return normalized

    parts = urlsplit(normalized)
    hostname = (parts.hostname or '').strip().lower()
    if hostname not in {'127.0.0.1', 'localhost'}:
        return normalized.rstrip('/')

    port = f':{parts.port}' if parts.port is not None else ''
    auth = ''
    if parts.username:
        auth = parts.username
        if parts.password:
            auth += f':{parts.password}'
        auth += '@'
    netloc = f'{auth}host.docker.internal{port}'
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment)).rstrip('/')


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
    )

    app_name: str = 'Campus Task Platform API'
    env: str = 'dev'
    api_v1_prefix: str = '/api/v1'

    secret_key: str = 'please-change-me'
    access_token_expire_minutes: int = 60 * 24 * 30  # 30天

    database_url: str = 'sqlite:///./campus_task.db'
    redis_url: str = ''
    agent_queue_key_prefix: str = 'campus_task:agent_queue'
    agent_gateway_public_base_url: str = ''
    agent_gateway_timeout_seconds: int = 600
    agent_gateway_token_expire_minutes: int = 120
    agent_run_silence_timeout_seconds: int = 300
    agent_run_max_seconds: int = 1800
    agent_upstream_kimi_api_key: str = ''
    agent_upstream_kimi_base_url: str = 'https://api.kimi.com/coding/v1'
    agent_upstream_kimi_search_url: str = ''
    agent_upstream_kimi_fetch_url: str = ''
    backend_public_url_dev: str = 'http://127.0.0.1:8000'
    backend_public_url_prod: str = 'https://api.example.com'
    frontend_public_url_dev: str = 'http://localhost:5173'
    frontend_public_url_prod: str = 'https://app.example.com'
    cors_origins: str = ''

    third_party_auth_url: str
    password_encryption: bool = True
    registration_default_enabled: bool = True

    admin_account: str
    admin_password: str

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {'prod', 'production'}

    @property
    def is_development(self) -> bool:
        return self.env.lower() in {'dev', 'development', 'local'}

    @property
    def debug(self) -> bool:
        return self.is_development

    @property
    def log_level(self) -> str:
        return 'DEBUG' if self.is_development else 'INFO'

    @property
    def backend_public_url(self) -> str:
        return self.backend_public_url_prod if self.is_production else self.backend_public_url_dev

    @property
    def frontend_public_url(self) -> str:
        return self.frontend_public_url_prod if self.is_production else self.frontend_public_url_dev

    @property
    def agent_gateway_origin(self) -> str:
        configured = self.agent_gateway_public_base_url.strip()
        if configured:
            return configured.rstrip('/')
        return _replace_localhost_for_docker(self.backend_public_url)

    @property
    def agent_gateway_base_url(self) -> str:
        return f'{self.agent_gateway_origin}{self.api_v1_prefix}/agent/gateway'

    @property
    def resolved_agent_upstream_kimi_search_url(self) -> str:
        configured = self.agent_upstream_kimi_search_url.strip()
        if configured:
            return configured.rstrip('/')
        return f'{self.agent_upstream_kimi_base_url.rstrip("/")}/search'

    @property
    def resolved_agent_upstream_kimi_fetch_url(self) -> str:
        configured = self.agent_upstream_kimi_fetch_url.strip()
        if configured:
            return configured.rstrip('/')
        return f'{self.agent_upstream_kimi_base_url.rstrip("/")}/fetch'

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip():
            return [item.strip() for item in self.cors_origins.split(',') if item.strip()]

        if self.is_production:
            return [self.frontend_public_url_prod]

        dev_defaults = [
            self.frontend_public_url_dev,
            'http://localhost:5173',
            'http://127.0.0.1:5173',
            'http://localhost:4173',
            'http://127.0.0.1:4173',
        ]
        seen: set[str] = set()
        deduped: list[str] = []
        for origin in dev_defaults:
            if origin not in seen:
                deduped.append(origin)
                seen.add(origin)
        return deduped


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
