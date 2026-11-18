import asyncio
import gzip
import json
import struct
import unittest
from unittest.mock import patch

import websockets
from x2_agent import asr as agent


class StreamingAsrTests(unittest.IsolatedAsyncioTestCase):
    async def test_hotwords_are_sent_in_wire_request_and_text_stays_unmodified(self):
        configs = []

        async def server(ws):
            config = await ws.recv()
            configs.append(json.loads(gzip.decompress(config[8:]).decode()))
            async for packet in ws:
                if packet[1] & 2:
                    body = json.dumps({'result': {'text': '梅西梅西'}}).encode()
                    await ws.send(bytes([0x11, 0x93, 0x10, 0]) +
                                  struct.pack('>iI', -1, len(body)) + body)
                    return

        async with websockets.serve(server, '127.0.0.1', 0) as listener:
            url = 'ws://127.0.0.1:%d' % listener.sockets[0].getsockname()[1]
            for raw in ('["灵犀", "灵犀"]', '[]'):
                with patch.dict(agent.os.environ, {"DOUBAO_ASR_HOTWORDS": raw}):
                    text = await agent.asr_transcribe(b"12", "test", "test", url)
                    self.assertEqual(text, "梅西梅西")
        context = json.loads(configs[0]["request"]["corpus"]["context"])
        self.assertEqual(context, {"hotwords": [{"word": "灵犀"}]})
        self.assertNotIn("corpus", configs[1]["request"])

    def test_invalid_hotwords_fail_clearly(self):
        for raw in ('灵犀', '{"word":"灵犀"}', '[null]', '[""]'):
            with patch.dict(agent.os.environ, {"DOUBAO_ASR_HOTWORDS": raw}):
                with self.assertRaises(ValueError):
                    agent.configured_hotwords()

    async def test_upload_before_commit_and_binary_final_without_disconnect(self):
        uploaded = asyncio.Event()
        packets = []

        async def server(ws):
            await ws.recv()  # configuration
            async for packet in ws:
                size = struct.unpack('>I', packet[4:8])[0]
                packets.append(packet[8:8 + size])
                if packet[1] & 2:
                    body = json.dumps({'result': {'text': '测试成功'}}).encode()
                    # final flag + sequence, with NO JSON is_final
                    await ws.send(bytes([0x11, 0x93, 0x10, 0]) +
                                  struct.pack('>iI', -1, len(body)) + body)
                    await ws.wait_closed()  # client must not wait for server close
                    return
                uploaded.set()

        async with websockets.serve(server, '127.0.0.1', 0) as listener:
            url = 'ws://127.0.0.1:%d' % listener.sockets[0].getsockname()[1]
            with patch.object(agent, 'ASR_WS_URL', url):
                stream = agent.StreamingAsr('test-key', 'test-resource')
                try:
                    pcm = bytes(range(256)) * 37  # full packet plus tail
                    stream.feed(pcm)
                    await asyncio.wait_for(uploaded.wait(), 2)
                    self.assertFalse(stream.task.done())
                    result = await asyncio.wait_for(stream.finish(), 2)
                    self.assertEqual(result, '测试成功')
                    self.assertEqual(b''.join(packets), pcm)
                finally:
                    await stream.close()

    async def test_connection_failure_reaches_commit(self):
        with patch.object(agent.websockets, 'connect', side_effect=OSError('offline')):
            stream = agent.StreamingAsr('test-key', 'test-resource')
            try:
                stream.feed(b'1234')
                with self.assertRaisesRegex(OSError, 'offline'):
                    await stream.finish()
            finally:
                await stream.close()

    async def test_abandoned_recording_cancels_upload(self):
        entered, cancelled = asyncio.Event(), asyncio.Event()

        async def blocked(*args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with patch.object(agent, 'asr_stream_transcribe', blocked):
            stream = agent.StreamingAsr('test-key', 'test-resource')
            await entered.wait()
            await stream.close()
            self.assertTrue(cancelled.is_set())
            self.assertTrue(stream.task.cancelled())

    async def test_upload_backlog_fails_without_hanging(self):
        stream = agent.StreamingAsr('test-key', 'test-resource')
        try:
            for _ in range(stream.queue.maxsize + 1):
                stream.feed(b'12')
            with self.assertRaisesRegex(RuntimeError, '积压'):
                await asyncio.wait_for(stream.finish(), 1)
        finally:
            await stream.close()


if __name__ == '__main__':
    unittest.main()
