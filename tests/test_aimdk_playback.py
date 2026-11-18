import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from x2_agent.aimdk_playback import AimdkPcmPlayer, AudioFocusError


class Request:
    def __init__(self):
        self.focus_requester = SimpleNamespace(pkg_name="", priority=0, priority_weight=0)


class Service:
    Request = Request


class Message:
    def __init__(self):
        self.info = SimpleNamespace()
        self.data = SimpleNamespace()


class PlaybackTests(unittest.IsolatedAsyncioTestCase):
    async def test_focus_client_waits_for_dds_discovery(self):
        player = AimdkPcmPlayer.__new__(AimdkPcmPlayer)
        player.node = object()
        player.ros = SimpleNamespace(spin_once=lambda node, timeout_sec=0: None)
        checks = 0
        expected = object()

        class Client:
            def service_is_ready(self):
                nonlocal checks
                checks += 1
                return checks >= 3

            def call_async(self, request):
                return SimpleNamespace(done=lambda: True, result=lambda: expected)

        result = await player._call(Client(), Request(), timeout=0.2)
        self.assertIs(result, expected)
        self.assertGreaterEqual(checks, 3)

    def make_player(self, granted=True, release_confirmed=True):
        player = AimdkPcmPlayer.__new__(AimdkPcmPlayer)
        player.pkg_name = "eldercare_agent"
        player.priority = 6
        player.RequestAudioFocus = Service
        player.AbandonAudioFocus = Service
        player.request_client = "request"
        player.abandon_client = "abandon"
        player.AudioPlayback = Message
        player._has_focus = False
        player._token = ""
        player._next_publish_time = 0
        player._lock = asyncio.Lock()
        published = []
        player.publisher = SimpleNamespace(publish=published.append)
        player.node = SimpleNamespace(get_clock=lambda: SimpleNamespace(
            now=lambda: SimpleNamespace(to_msg=lambda: "stamp")))
        player.ros = SimpleNamespace(spin_once=lambda node, timeout_sec=0: None)
        calls = []

        async def call(client, request):
            calls.append((client, request.focus_requester.pkg_name,
                          request.focus_requester.priority,
                          request.focus_requester.priority_weight))
            return SimpleNamespace(reponse=SimpleNamespace(
                status=SimpleNamespace(value=1)),
                focus_response=SimpleNamespace(focus_gain=(
                    granted if client == "request" else not release_confirmed)))

        player._call = call
        return player, published, calls

    async def test_bounded_lead_avoids_per_packet_drift_and_keeps_all_pcm(self):
        player, published, _ = self.make_player()
        clock = SimpleNamespace(value=100.0)
        async def sleep(delay):
            clock.value += max(0, delay)
        times = []
        def publish(msg):
            times.append(clock.value)
            published.append(msg)
            clock.value += .004  # ROS publish/scheduling overhead.
        player.publisher.publish = publish
        with patch("x2_agent.aimdk_playback.time", SimpleNamespace(monotonic=lambda: clock.value)), patch("x2_agent.aimdk_playback.asyncio.sleep", sleep):
            await player.begin()
            pcm = b"\x01\x00" * 16000
            await player.write(pcm)
            await player.end()
        self.assertEqual(b"".join(bytes(msg.data.data) for msg in published), pcm)
        self.assertEqual(len({msg.token_id for msg in published}), 1)
        self.assertLess(times[-1] - times[0], .8)
        self.assertGreaterEqual(clock.value, 101.0)
        self.assertLess(clock.value, 101.02)
        self.assertEqual(player._max_publish_lag_ms, 0)
        self.assertFalse(player._has_focus)

    async def test_long_supply_gap_is_reported_without_changing_token(self):
        player, published, _ = self.make_player()
        clock = SimpleNamespace(value=100.0)
        async def sleep(delay):
            clock.value += max(0, delay)
        with patch("x2_agent.aimdk_playback.time", SimpleNamespace(monotonic=lambda: clock.value)), patch("x2_agent.aimdk_playback.asyncio.sleep", sleep):
            await player.begin()
            await player.write(b"\x01\x00" * 4800)
            clock.value += .8  # Simulate a cloud/network stall beyond the lead.
            await player.write(b"\x02\x00" * 1600)
            await player.end()
        self.assertGreater(player._max_publish_lag_ms, 300)
        self.assertEqual(len({msg.token_id for msg in published}), 1)
        self.assertEqual(player._published_bytes, 12800)

    async def test_focus_denial_never_publishes(self):
        player, published, calls = self.make_player(granted=False)
        with self.assertRaises(AudioFocusError):
            await player.begin()
        self.assertFalse(player._lock.locked())
        self.assertEqual(published, [])
        self.assertEqual(calls[0], ("request", "eldercare_agent", 6, 0))

    async def test_pcm_format_and_focus_release_match(self):
        player, published, calls = self.make_player()
        await player.begin()
        await player.write(b"\x01\x00\x02\x00")
        await player.end()
        self.assertEqual(len(published), 1)
        msg = published[0]
        self.assertEqual((msg.info.channels, msg.info.sample_rate,
                          msg.info.sample_format, msg.info.coding_format),
                         (1, 16000, "S16LE", "pcm"))
        self.assertEqual(msg.data.data, [1, 0, 2, 0])
        self.assertEqual(msg.pkg_name, "eldercare_agent")
        self.assertEqual(calls[0][1:], calls[1][1:])
        self.assertFalse(player._has_focus)

    async def test_odd_pcm_rejected_and_focus_still_released(self):
        player, published, _ = self.make_player()
        await player.begin()
        try:
            with self.assertRaises(ValueError):
                await player.write(b"\x01")
        finally:
            await player.end()
        self.assertEqual(published, [])

    async def test_focus_loss_notification_stops_next_pcm_publish(self):
        player, published, _ = self.make_player()
        await player.begin()
        player.ros.spin_once = lambda node, timeout_sec=0: player._on_focus_response(
            SimpleNamespace(pkg_name=player.pkg_name, focus_gain=False))
        with self.assertRaisesRegex(AudioFocusError, "抢占"):
            await player.write(b"\x01\x00")
        await player.end()
        self.assertEqual(published, [])

    async def test_release_must_be_confirmed_by_focus_response(self):
        player, published, _ = self.make_player(release_confirmed=False)
        await player.begin()
        with self.assertRaisesRegex(AudioFocusError, "释放音频焦点结果未确认"):
            await player.end()
        self.assertTrue(player._has_focus)
        self.assertEqual(published, [])

    async def test_second_identical_release_confirms_v1_focus_result(self):
        player, _, _ = self.make_player()
        original_call = player._call
        release_count = 0

        async def call(client, request):
            nonlocal release_count
            if client == "abandon":
                release_count += 1
                return SimpleNamespace(
                    reponse=SimpleNamespace(status=SimpleNamespace(value=1)),
                    focus_response=SimpleNamespace(focus_gain=release_count == 1))
            return await original_call(client, request)

        player._call = call
        await player.begin()
        await player.end()
        self.assertEqual(release_count, 2)
        self.assertFalse(player._has_focus)

    def test_close_after_ros_sigint_shutdown(self):
        player = AimdkPcmPlayer.__new__(AimdkPcmPlayer)
        player._has_focus = False
        player.owns_node = True
        destroyed = []
        shutdown = []
        player.node = SimpleNamespace(destroy_node=lambda: destroyed.append(True))
        player.ros = SimpleNamespace(ok=lambda: False,
                                     shutdown=lambda: shutdown.append(True))
        player.close()
        self.assertEqual(destroyed, [True])
        self.assertEqual(shutdown, [])


if __name__ == "__main__":
    unittest.main()
