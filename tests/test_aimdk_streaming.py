import base64
import unittest

from x2_agent.aimdk_streaming import StreamingVadInput
from x2_agent.gateway import T


class StreamingVadTests(unittest.TestCase):
    def test_start_and_pcm_arrive_before_end(self):
        frames = []
        stream = StreamingVadInput(frames.append)
        stream.feed(1, 1, b"12", 0)
        stream.feed(1, 2, b"34", .1)
        self.assertEqual([f["type"] for f in frames],
                         [T["a_start"], T["a_append"], T["a_append"]])
        stream.feed(1, 3, b"56", .2)
        self.assertEqual(frames[-1]["type"], T["a_commit"])
        self.assertEqual(b"".join(base64.b64decode(f["audio"]) for f in frames
                                 if f["type"] == T["a_append"]), b"123456")
        self.assertEqual(len({f["eventId"] for f in frames}), 1)

    def test_new_begin_cancels_incomplete_audio_instead_of_joining(self):
        frames = []
        stream = StreamingVadInput(frames.append)
        stream.feed(1, 1, b"old", 0)
        first = frames[0]["eventId"]
        stream.feed(1, 1, b"new", .1)
        self.assertEqual(frames[2], {"type": T["a_cancel"], "eventId": first})
        stream.feed(1, 3, b"", .2)
        self.assertNotEqual(first, frames[-1]["eventId"])

    def test_missing_end_commits_once_and_blocks_echo_until_resume(self):
        frames = []
        stream = StreamingVadInput(frames.append, idle_seconds=1.5)
        stream.feed(1, 1, b"12", 0)
        stream.check_idle(1)
        self.assertNotEqual(frames[-1]["type"], T["a_commit"])
        stream.check_idle(1.6)
        self.assertEqual(frames[-1]["boundary"], "idle_timeout")
        count = len(frames)
        stream.feed(1, 1, b"echo", 2)
        stream.check_idle(3)
        self.assertEqual(len(frames), count)
        stream.resume()
        stream.feed(1, 1, b"new", 4)
        self.assertGreater(len(frames), count)

    def test_oversize_is_cancelled_without_commit(self):
        frames = []
        stream = StreamingVadInput(frames.append, max_seconds=.001)
        stream.feed(1, 1, b"x" * 40, 0)
        self.assertEqual(frames[-1]["type"], T["a_cancel"])
        stream.feed(1, 2, b"tail", .1)
        stream.feed(1, 3, b"", .2)
        self.assertFalse(any(f["type"] == T["a_commit"] for f in frames))
