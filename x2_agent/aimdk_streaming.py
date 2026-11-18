"""Bounded live VAD events for the shared streaming ASR interface."""
import base64
import time
import uuid

from .aimdk_audio import PCM_BYTES_PER_SECOND
from .gateway import T


class StreamingVadInput:
    def __init__(self, emit, *, stream_id=1, idle_seconds=0, max_seconds=20):
        self.emit = emit
        self.stream_id = stream_id
        self.idle_seconds = idle_seconds
        self.max_seconds = max_seconds
        self.event_id = None
        self.started = self.last = None
        self.size = 0
        self.blocked = False
        self.awaiting_reply = False

    def cancel(self):
        if self.event_id:
            self.emit({"type": T["a_cancel"], "eventId": self.event_id})
        self.event_id = None
        self.started = self.last = None
        self.size = 0

    def resume(self):
        self.cancel()
        self.awaiting_reply = False

    def feed(self, stream_id, state, data, now=None):
        if stream_id != self.stream_id or self.awaiting_reply:
            return
        now = time.monotonic() if now is None else now
        if state not in (1, 2, 3):
            return
        if state == 1:
            self.cancel()
            self.blocked = False
        if self.blocked:
            return
        if self.event_id is None:
            if state == 3:
                return
            self.event_id = "aimdk-" + uuid.uuid4().hex[:12]
            self.started = now
            self.emit({"type": T["a_start"], "eventId": self.event_id})
        self.last = now
        if (now - self.started > self.max_seconds or
                self.size + len(data) > self.max_seconds * PCM_BYTES_PER_SECOND):
            self.cancel()
            self.blocked = True
            return
        self.size += len(data)
        for offset in range(0, len(data), 6400):
            self.emit({"type": T["a_append"], "eventId": self.event_id,
                       "audio": base64.b64encode(bytes(data[offset:offset + 6400])).decode("ascii")})
        if state == 3:
            self.commit("end")

    def commit(self, boundary):
        if self.event_id is None:
            return
        if not self.size:
            self.cancel()
            return
        self.emit({"type": T["a_commit"], "eventId": self.event_id,
                   "boundary": boundary, "pcmBytes": self.size})
        self.event_id = None
        self.started = self.last = None
        self.size = 0
        self.awaiting_reply = True

    def check_idle(self, now=None):
        now = time.monotonic() if now is None else now
        if (self.idle_seconds and self.last is not None and
                now - self.last >= self.idle_seconds):
            self.commit("idle_timeout")
