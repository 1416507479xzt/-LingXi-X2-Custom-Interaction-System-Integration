import asyncio
import unittest
from unittest.mock import patch

import httpx

from x2_agent.llm import LlmClient, RequestTiming


class LatencyTests(unittest.IsolatedAsyncioTestCase):
    async def client(self, responder):
        http = httpx.AsyncClient(transport=httpx.MockTransport(responder), trust_env=False)
        with patch("x2_agent.llm.httpx.AsyncClient", return_value=http):
            client = LlmClient()
        client.last_used = float("-inf")
        self.addAsyncCleanup(client.close)
        return client

    async def test_concurrent_preconnects_share_one_head_without_model_payload(self):
        requests = []
        async def respond(request):
            requests.append(request)
            await asyncio.sleep(.01)
            return httpx.Response(404)
        client = await self.client(respond)
        await asyncio.gather(client.warm("test-key"), client.warm("test-key"))
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].method, "HEAD")
        self.assertEqual(requests[0].content, b"")
        self.assertEqual(requests[0].extensions["timeout"]["connect"], 1)

    async def test_active_stream_skips_head_and_closing_releases_inner_stream(self):
        requests = []
        client = await self.client(lambda r: requests.append(r) or httpx.Response(404))
        closed = asyncio.Event()
        async def source(*args):
            try:
                yield "text", "unchanged"
                await asyncio.Event().wait()
            finally:
                closed.set()
        with patch.object(client, "_stream", source):
            stream = client.stream("system", [], "model", "test-key")
            self.assertEqual(await anext(stream), ("text", "unchanged"))
            await client.warm("test-key")
            self.assertEqual(requests, [])
            await stream.aclose()
            self.assertTrue(closed.is_set())
            self.assertEqual(client._active_requests, 0)
        await client.warm("test-key")
        self.assertEqual(len(requests), 1)

    async def test_idle_maintenance_survives_failure_and_stops_with_client(self):
        calls = []
        recovered = asyncio.Event()
        def respond(request):
            calls.append(request.method)
            if len(calls) == 1:
                raise httpx.ReadTimeout("synthetic")
            recovered.set()
            return httpx.Response(404)
        client = await self.client(respond)
        with patch("x2_agent.llm.IDLE_KEEPALIVE_SECONDS", .01):
            client.start_keepalive("test-key")
            task = client._keepalive_task
            client.start_keepalive("test-key")
            self.assertIs(client._keepalive_task, task)
            await asyncio.wait_for(recovered.wait(), 1)
            await client.close()
            self.assertTrue(task.done())
            self.assertIsNone(client._keepalive_task)
        self.assertTrue(all(method == "HEAD" for method in calls))

    async def test_preconnect_has_a_total_deadline_and_cancels_stalled_head(self):
        cancelled = asyncio.Event()
        async def respond(request):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
        client = await self.client(respond)
        started = asyncio.get_running_loop().time()
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(client.warm("test-key"), 2)
        self.assertLess(asyncio.get_running_loop().time() - started, 1.8)
        self.assertTrue(cancelled.is_set())
        self.assertEqual(client.last_used, float("-inf"))

    async def test_timing_reports_only_durations_and_connection_presence(self):
        timing = RequestTiming()
        await timing.trace("connection.connect_tcp.started", {"Authorization": "secret"})
        await timing.trace("connection.connect_tcp.complete", {"return_value": "secret"})
        await timing.trace("connection.start_tls.started", {})
        await timing.trace("connection.start_tls.complete", {})
        with self.assertLogs("x2_agent.llm", level="INFO") as captured:
            timing.report("headers")
        log = " ".join(captured.output)
        self.assertIn("new_connection=True", log)
        self.assertIn("tcp_ms=", log)
        self.assertNotIn("secret", log)
        self.assertFalse(RequestTiming().new_connection)
