"""Reusable async HTTP/SSE connection for Ark chat completions."""
import asyncio
from contextlib import aclosing, suppress
import json
import logging
import os
import time
from typing import AsyncIterator, Dict, Any, List, Optional, Set, Tuple

import httpx

# 火山方舟 API 端点 - 可通过环境变量覆盖
ARK_API_URL = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'

# HTTP 连接参数
HTTP_TIMEOUT_SECONDS = 60
HTTP_CONNECT_TIMEOUT_SECONDS = 10
HTTP_MAX_CONNECTIONS = 2
HTTP_KEEPALIVE_EXPIRY_SECONDS = 120
HTTP_WARM_INTERVAL_SECONDS = 60  # 连接预热的最小间隔
IDLE_KEEPALIVE_SECONDS = 20
logger = logging.getLogger(__name__)


class RequestTiming:
    """Record timing only; never log trace info containing headers or credentials."""
    def __init__(self):
        self.started = time.perf_counter()
        self.starts = {}
        self.durations = {}
        self.new_connection = False

    async def trace(self, name, info):
        event, _, state = name.rpartition(".")
        if event.rsplit(".", 1)[-1] not in {"connect_tcp", "start_tls"}:
            return
        now = time.perf_counter()
        if state == "started":
            self.starts[event] = now
            self.new_connection = True
        elif state in {"complete", "failed"} and event in self.starts:
            self.durations[event] = self.durations.get(event, 0) + (now - self.starts.pop(event)) * 1000

    def report(self, phase):
        logger.info("LLM连接计时 phase=%s new_connection=%s tcp_ms=%.0f tls_ms=%.0f elapsed_ms=%.0f",
                    phase, self.new_connection,
                    sum(value for name, value in self.durations.items() if name.endswith(".connect_tcp")),
                    sum(value for name, value in self.durations.items() if name.endswith(".start_tls")),
                    (time.perf_counter() - self.started) * 1000)


class LlmClient:
    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint or os.environ.get("ARK_API_URL", ARK_API_URL)
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(HTTP_TIMEOUT_SECONDS, connect=HTTP_CONNECT_TIMEOUT_SECONDS),
            limits=httpx.Limits(max_connections=HTTP_MAX_CONNECTIONS,
                               max_keepalive_connections=HTTP_MAX_CONNECTIONS,
                               keepalive_expiry=HTTP_KEEPALIVE_EXPIRY_SECONDS))
        self.unsupported_thinking: Set[str] = set()
        self.last_used = 0.0
        self._warm_lock = asyncio.Lock()
        self._active_requests = 0
        self._keepalive_task = None

    def start_keepalive(self, api_key: str) -> None:
        """Opt in from an active agent; HEAD only, no background model inference."""
        if self._keepalive_task is None or self._keepalive_task.done():
            self._keepalive_task = asyncio.create_task(self._keepalive(api_key))

    async def _keepalive(self, api_key):
        while True:
            await asyncio.sleep(min(5, IDLE_KEEPALIVE_SECONDS))
            try:
                await self._warm(api_key, IDLE_KEEPALIVE_SECONDS)
            except Exception as exc:
                logger.debug("LLM空闲保温失败，保留正常请求路径: %s", type(exc).__name__)

    async def warm(self, api_key: str) -> None:
        await self._warm(api_key, HTTP_WARM_INTERVAL_SECONDS)

    async def _warm(self, api_key, interval):
        async with self._warm_lock:
            if self._active_requests or time.perf_counter() - self.last_used < interval:
                return
            # HEAD does not submit model messages. POST independently checks
            # authorization; a preconnect response is not an inference result.
            timing = RequestTiming()
            await asyncio.wait_for(
                self.http.head(self.endpoint, headers={'Authorization': 'Bearer ' + api_key},
                               timeout=httpx.Timeout(1, connect=1),
                               extensions={"trace": timing.trace}), timeout=1)
            self.last_used = time.perf_counter()
            timing.report("preconnect")

    async def close(self) -> None:
        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._keepalive_task
            self._keepalive_task = None
        await self.http.aclose()

    async def stream(self, system_prompt: str, history: List[Dict[str, Any]],
                     model: str, api_key: str,
                     tools: Optional[List[Dict[str, Any]]] = None) -> AsyncIterator[Tuple[str, Any]]:
        self._active_requests += 1
        try:
            async with aclosing(self._stream(system_prompt, history, model, api_key, tools)) as source:
                async for item in source:
                    yield item
        finally:
            self._active_requests -= 1

    async def _stream(self, system_prompt, history, model, api_key, tools):
        payload = {'model': model,
                   'messages': [{'role': 'system', 'content': system_prompt}] + list(history),
                   'temperature': 0.7, 'stream': True}
        if tools:
            payload['tools'] = tools
        if model not in self.unsupported_thinking:
            payload['thinking'] = {'type': 'disabled'}
        started = time.perf_counter()
        first = True
        tc_acc = {}
        for attempt in range(2):
            timing = RequestTiming()
            async with self.http.stream('POST', self.endpoint, json=payload,
                                        headers={'Authorization': 'Bearer ' + api_key},
                                        extensions={"trace": timing.trace}) as resp:
                timing.report("headers")
                if resp.status_code >= 400:
                    error = (await resp.aread()).decode('utf-8', errors='replace')
                    lower = error.lower()
                    if (attempt == 0 and resp.status_code == 400 and 'thinking' in payload
                            and 'thinking' in lower and any(word in lower for word in
                            ('not support', 'unsupported', 'unknown', 'unrecognized'))):
                        self.unsupported_thinking.add(model)
                        payload.pop('thinking')
                        print('agent     模型不支持 thinking 参数，重试一次并缓存结果')
                        continue
                    raise RuntimeError('LLM HTTP %s: %s' % (resp.status_code, error[:500]))
                print('agent     [LLM HTTP %.0fms]' % ((time.perf_counter() - started) * 1000))
                async for line in resp.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    data = line[5:].strip()
                    if data == '[DONE]':
                        # Consume the complete HTTP body to return the socket to the pool.
                        continue
                    chunk = json.loads(data)
                    choices = chunk.get('choices') or []
                    if not choices:
                        continue
                    delta = choices[0].get('delta') or {}
                    if first and (delta.get('content') or delta.get('tool_calls')):
                        first = False
                        timing.report("first_token")
                        print('agent     [LLM 首 token %.0fms] %s'
                              % ((time.perf_counter() - started) * 1000,
                                 '文本' if delta.get('content') else '工具调用'))
                    if delta.get('content'):
                        yield 'text', delta['content']
                    for call in delta.get('tool_calls') or []:
                        slot = tc_acc.setdefault(call.get('index', 0),
                                                 {'id': '', 'name': '', 'arguments': ''})
                        if call.get('id'):
                            slot['id'] = call['id']
                        fn = call.get('function') or {}
                        slot['name'] += fn.get('name') or ''
                        slot['arguments'] += fn.get('arguments') or ''
                self.last_used = time.perf_counter()
                break
        if tc_acc:
            yield 'tool_calls', [tc_acc[i] for i in sorted(tc_acc)]
