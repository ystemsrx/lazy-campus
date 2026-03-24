import logging
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.core.config import settings

logger = logging.getLogger(__name__)

_HOP_BY_HOP_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',
    'transfer-encoding',
    'upgrade',
}


@dataclass(frozen=True)
class AgentUpstreamTarget:
    url: str
    api_key: str


def _require_upstream_value(value: str, env_name: str) -> str:
    normalized = (value or '').strip()
    if normalized:
        return normalized
    raise HTTPException(status_code=503, detail=f'AI 代理上游未配置：{env_name}')


def _join_url(base_url: str, path: str = '') -> str:
    normalized_base = base_url.rstrip('/')
    normalized_path = path.lstrip('/')
    if not normalized_path:
        return normalized_base
    return f'{normalized_base}/{normalized_path}'


def get_kimi_provider_target(path: str = '') -> AgentUpstreamTarget:
    return AgentUpstreamTarget(
        url=_join_url(
            _require_upstream_value(settings.agent_upstream_kimi_base_url, 'AGENT_UPSTREAM_KIMI_BASE_URL'),
            path,
        ),
        api_key=_require_upstream_value(settings.agent_upstream_kimi_api_key, 'AGENT_UPSTREAM_KIMI_API_KEY'),
    )


def get_kimi_search_target() -> AgentUpstreamTarget:
    return AgentUpstreamTarget(
        url=_require_upstream_value(
            settings.resolved_agent_upstream_kimi_search_url,
            'AGENT_UPSTREAM_KIMI_SEARCH_URL',
        ),
        api_key=_require_upstream_value(settings.agent_upstream_kimi_api_key, 'AGENT_UPSTREAM_KIMI_API_KEY'),
    )


def get_kimi_fetch_target() -> AgentUpstreamTarget:
    return AgentUpstreamTarget(
        url=_require_upstream_value(
            settings.resolved_agent_upstream_kimi_fetch_url,
            'AGENT_UPSTREAM_KIMI_FETCH_URL',
        ),
        api_key=_require_upstream_value(settings.agent_upstream_kimi_api_key, 'AGENT_UPSTREAM_KIMI_API_KEY'),
    )


def _build_upstream_request_headers(request: Request, api_key: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in request.headers.items():
        lower_name = name.lower()
        if lower_name in _HOP_BY_HOP_HEADERS or lower_name in {'authorization', 'content-length', 'host'}:
            continue
        headers[name] = value
    headers['Authorization'] = f'Bearer {api_key}'
    return headers


def _build_downstream_response_headers(response: httpx.Response) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in response.headers.items():
        lower_name = name.lower()
        if lower_name in _HOP_BY_HOP_HEADERS or lower_name == 'content-length':
            continue
        headers[name] = value
    return headers


async def _close_upstream_stream(response: httpx.Response, client: httpx.AsyncClient) -> None:
    await response.aclose()
    await client.aclose()


async def proxy_agent_gateway_request(
    request: Request,
    target: AgentUpstreamTarget,
) -> StreamingResponse:
    body = await request.body()
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.agent_gateway_timeout_seconds),
        follow_redirects=True,
    )
    try:
        upstream_request = client.build_request(
            request.method,
            target.url,
            headers=_build_upstream_request_headers(request, target.api_key),
            params=request.query_params.multi_items(),
            content=body or None,
        )
        upstream_response = await client.send(upstream_request, stream=True)
    except httpx.TimeoutException as exc:
        await client.aclose()
        raise HTTPException(status_code=504, detail='AI 代理网关请求上游超时') from exc
    except httpx.HTTPError as exc:
        await client.aclose()
        logger.warning('agent gateway upstream request failed: %s', exc)
        raise HTTPException(status_code=502, detail='AI 代理网关请求上游失败') from exc

    return StreamingResponse(
        upstream_response.aiter_raw(),
        status_code=upstream_response.status_code,
        headers=_build_downstream_response_headers(upstream_response),
        background=BackgroundTask(_close_upstream_stream, upstream_response, client),
    )
