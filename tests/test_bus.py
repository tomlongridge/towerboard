import threading
import unittest

from tower.clock import FakeClock
from tower.events import Envelope
from tower.web.events import EventBus, Subscriber, stream


class SubscriberTest(unittest.TestCase):
    def test_drop_oldest_when_full(self):
        s = Subscriber(maxlen=3)
        for i in range(5):
            s.put(str(i))
        self.assertEqual(s.get(0), ["2", "3", "4"])
        self.assertEqual(s.dropped, 2)


class BusTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock(10.0)
        self.bus = EventBus(self.clock)

    def test_fan_out_and_slow_client_isolation(self):
        fast, slow = self.bus.subscribe(), self.bus.subscribe()
        slow.queue = type(slow.queue)(maxlen=2)
        for i in range(5):
            self.bus.publish(Envelope("strike", i, float(i), {"bell": 1}))
        self.assertEqual(len(fast.get(0)), 5)
        self.assertEqual(len(slow.get(0)), 2)
        self.assertEqual(self.bus.stats()["dropped"], 3)
        self.bus.unsubscribe(slow)
        self.assertEqual(self.bus.stats(), {"clients": 1, "dropped": 3, "dropped_by_client": [0]})

    def test_rt_status_kept_not_broadcast(self):
        sub = self.bus.subscribe()
        self.bus.on_rt({"schema_version": 1, "type": "system", "seq": 1, "t": 1.0, "payload": {"rt": {"x": 1}}})
        self.assertEqual(self.bus.rt_status, {"x": 1})
        self.assertTrue(self.bus.rt_fresh())
        self.assertEqual(sub.get(0), [])
        self.clock.advance(11)
        self.assertFalse(self.bus.rt_fresh())

    def test_bad_rt_envelope_counted(self):
        self.bus.on_rt({"type": "strike"})
        self.assertEqual(self.bus.rt_bad, 1)

    def test_stream_sends_snapshot_then_events(self):
        writes = []
        stop = threading.Event()

        def write(data):
            writes.append(data)
            if len(writes) == 2:
                stop.set()

        t = threading.Thread(target=stream, args=(self.bus, lambda: {"hello": 1}, write, stop, 0.05))
        t.start()
        for _ in range(100):
            if self.bus.stats()["clients"]:
                break
            threading.Event().wait(0.01)
        self.bus.publish(Envelope("strike", 9, 1.0, {"bell": 2}))
        t.join(2)
        self.assertIn(b'"type":"state"', writes[0])
        self.assertIn(b'"hello":1', writes[0])
        self.assertTrue(writes[1].startswith(b"data: ") or writes[1].startswith(b": keepalive"))
        self.assertEqual(self.bus.stats()["clients"], 0)  # unsubscribed on exit

    def test_stream_ends_when_client_goes(self):
        def write(data):
            raise BrokenPipeError

        stream(self.bus, dict, write, threading.Event(), 0.01)
        self.assertEqual(self.bus.stats()["clients"], 0)
