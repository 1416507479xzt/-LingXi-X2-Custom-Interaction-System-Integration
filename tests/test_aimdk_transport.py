import asyncio
import base64
import json
from types import SimpleNamespace
import unittest

from x2_agent.aimdk_transport import AimdkLocalTransport
from x2_agent.agent_config import AgentConfig
from x2_agent.gateway import T
from x2_agent.aimdk_audio import VadAssembler


class FakePlayer:
    def __init__(self):
        self.calls = []

    async def begin(self):
        self.calls.append("begin")

    async def write(self, pcm):
        self.calls.append(bytes(pcm))

    async def end(self):
        self.calls.append("end")


class AimdkTransportTests(unittest.IsolatedAsyncioTestCase):
    def pending_transport(self, idle=1.5):
        transport = AimdkLocalTransport.__new__(AimdkLocalTransport)
        transport.collector = VadAssembler()
        transport.incoming = asyncio.Queue(maxsize=4)
        transport._speaking = False
        transport.idle_seconds = idle
        transport._last_received = 1.1
        transport.collector.feed(1, 1, b"12", 1.0)
        transport.collector.feed(1, 2, b"34", 1.1)
        return transport

    async def test_missing_end_is_recovered_once_only_after_idle(self):
        transport = self.pending_transport()
        transport._check_idle(2.0)
        self.assertTrue(transport.incoming.empty())
        transport._check_idle(2.7)
        self.assertEqual(transport.incoming.get_nowait(), b"1234")
        transport._check_idle(4.0)
        self.assertTrue(transport.incoming.empty())

    async def test_idle_recovery_disabled_or_speaking_does_not_submit(self):
        for idle, speaking in ((0, False), (1.5, True)):
            transport = self.pending_transport(idle)
            transport._speaking = speaking
            transport._check_idle(4.0)
            self.assertTrue(transport.incoming.empty())

    async def test_normal_end_is_not_duplicated_by_idle_recovery(self):
        transport = self.pending_transport()
        transport._queue_utterance(transport.collector.feed(1, 3, b"56", 1.2))
        transport._check_idle(4.0)
        self.assertEqual(transport.incoming.get_nowait(), b"123456")
        self.assertTrue(transport.incoming.empty())
    async def test_completed_vad_uses_existing_gateway_event_contract(self):
        transport = AimdkLocalTransport.__new__(AimdkLocalTransport)
        transport.incoming = asyncio.Queue()
        transport._closed = False
        transport._speaking = False
        await transport.incoming.put(b"\x00\x01" * 4000)
        frames = transport._frames()
        sync = json.loads(await anext(frames))
        start = json.loads(await anext(frames))
        first = json.loads(await anext(frames))
        second = json.loads(await anext(frames))
        commit = json.loads(await anext(frames))
        self.assertEqual([x["type"] for x in (sync, start, first, second, commit)],
                         [T["sync"], T["a_start"], T["a_append"],
                          T["a_append"], T["a_commit"]])
        self.assertEqual(start["eventId"], commit["eventId"])
        self.assertEqual(base64.b64decode(first["audio"] + "==") +
                         base64.b64decode(second["audio"] + "=="),
                         b"\x00\x01" * 4000)
        await frames.aclose()

    async def test_audio_output_requires_focus_and_releases_on_done(self):
        transport = AimdkLocalTransport.__new__(AimdkLocalTransport)
        transport.player = FakePlayer()
        transport._playing = False
        transport._speaking = False
        pcm = base64.b64encode(b"\x01\x00").decode("ascii")
        await transport.send(json.dumps({"type": T["tts_delta"], "audio": pcm}))
        await transport.send(json.dumps({"type": T["tts_done"]}))
        self.assertEqual(transport.player.calls, ["begin", b"\x01\x00", "end"])
        self.assertFalse(transport._speaking)

    def test_robot_audio_requires_explicit_opt_in(self):
        base = dict(speech_key="test", ark_key="test", competition_mode=True,
                    presentation_backend="none",
                    transport="aimdk")
        with self.assertRaisesRegex(ValueError, "enable-robot-audio"):
            AgentConfig(**base)
        AgentConfig(**base, enable_robot_audio=True)


if __name__ == "__main__":
    unittest.main()
