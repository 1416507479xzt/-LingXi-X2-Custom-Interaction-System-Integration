import asyncio
import unittest

from scripts.aimdk_asr_diagnostic import recognize_with_capture


class DiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def test_capture_continues_during_cloud_wait(self):
        spins = []

        async def recognition():
            await asyncio.sleep(0.03)
            self.assertGreaterEqual(len(spins), 2)
            return "你好灵犀"

        result = await recognize_with_capture(
            recognition(), lambda: spins.append(True), lambda: True)
        self.assertEqual(result, "你好灵犀")

    async def test_ros_stop_cancels_pending_cloud_request(self):
        cancelled = asyncio.Event()

        async def recognition():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        spins = []
        with self.assertRaisesRegex(RuntimeError, "ROS 已停止"):
            await recognize_with_capture(
                recognition(), lambda: spins.append(True), lambda: not spins)
        self.assertTrue(cancelled.is_set())
