import tempfile
import unittest
from pathlib import Path

from tower import ipc


class IpcTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir="/tmp"))

    def test_round_trip(self):
        rx = ipc.Receiver(self.dir / "e.sock")
        self.addCleanup(rx.close)
        tx = ipc.Sender(self.dir / "e.sock")
        self.addCleanup(tx.close)
        self.assertTrue(tx.send({"a": 1}))
        self.assertEqual(rx.recv(timeout=1), {"a": 1})
        self.assertIsNone(rx.recv(timeout=0.05))

    def test_sender_never_blocks_without_receiver(self):
        tx = ipc.Sender(self.dir / "missing.sock")
        self.addCleanup(tx.close)
        self.assertFalse(tx.send({"a": 1}))
        self.assertEqual(tx.dropped, 1)

    def test_full_receiver_drops_instead_of_blocking(self):
        rx = ipc.Receiver(self.dir / "f.sock")
        self.addCleanup(rx.close)
        tx = ipc.Sender(self.dir / "f.sock")
        self.addCleanup(tx.close)
        for _ in range(10000):  # nobody reading: the kernel buffer fills
            tx.send({"x": "y" * 500})
        self.assertGreater(tx.dropped, 0)

    def test_oversized_and_malformed(self):
        rx = ipc.Receiver(self.dir / "m.sock")
        self.addCleanup(rx.close)
        tx = ipc.Sender(self.dir / "m.sock")
        self.addCleanup(tx.close)
        self.assertFalse(tx.send({"x": "y" * 5000}))
        tx.sock.sendto(b"{not json", str(self.dir / "m.sock"))
        self.assertIsNone(rx.recv(timeout=1))
        self.assertEqual(rx.bad, 1)

    def test_stale_socket_replaced(self):
        ipc.Receiver(self.dir / "s.sock").sock.close()  # left behind by a crash
        rx = ipc.Receiver(self.dir / "s.sock")
        self.addCleanup(rx.close)
        tx = ipc.Sender(self.dir / "s.sock")
        self.addCleanup(tx.close)
        tx.send({"ok": True})
        self.assertEqual(rx.recv(timeout=1), {"ok": True})
