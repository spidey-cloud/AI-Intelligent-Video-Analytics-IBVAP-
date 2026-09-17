"""Realtime alert fan-out.

One hub, many channels:
  • WebSocket subscriptions (dashboard live alert panel)
  • in-memory ring for HTTP-poll fallback (unstable links)
Channel adapters (SMS gateway, C2 webhook) plug into push() – in production
they run async workers that drain per-channel queues (ARCHITECTURE.md §6).
"""
import queue
import threading
from collections import deque


class AlertHub:
    def __init__(self, maxlen=300):
        self._subs = set()
        self._lock = threading.Lock()
        self.recent = deque(maxlen=maxlen)

    def subscribe(self):
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subs.discard(q)

    def push(self, msg):
        with self._lock:
            self.recent.appendleft(msg)
            for q in self._subs:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass
