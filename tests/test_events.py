import json
import unittest

from tower.events import (
    SCHEMA_VERSION,
    ContractError,
    Envelope,
    Sequencer,
    from_dict,
    from_json,
    strike_payload,
)


class EnvelopeTest(unittest.TestCase):
    def test_round_trip(self):
        env = Envelope("strike", 7, 12.3456789, strike_payload(3, "hand", "live"))
        back = from_json(env.to_json())
        self.assertEqual(back.type, "strike")
        self.assertEqual(back.seq, 7)
        self.assertEqual(back.t, 12.345679)  # microsecond precision on the wire
        self.assertEqual(back.payload, {"bell": 3, "stroke": "hand", "source": "live"})
        self.assertEqual(back.schema_version, SCHEMA_VERSION)

    def test_wire_shape_matches_design(self):
        d = json.loads(Envelope("strike", 1, 0.5, {"bell": 1}).to_json())
        self.assertEqual(list(d), ["schema_version", "type", "seq", "t", "payload"])

    def test_single_line(self):
        line = Envelope("board", 1, 0.0, {"text": "a\nb"}).to_json()
        self.assertNotIn("\n", line)

    def test_rejects_newer_schema(self):
        with self.assertRaises(ContractError):
            from_dict({"schema_version": SCHEMA_VERSION + 1, "type": "strike", "seq": 1, "t": 0})

    def test_unknown_type_and_fields_tolerated_on_read(self):
        env = from_dict(
            {"schema_version": 1, "type": "future", "seq": 1, "t": 0, "payload": {"x": 1}, "extra": 2}
        )
        self.assertEqual(env.type, "future")

    def test_missing_fields(self):
        with self.assertRaisesRegex(ContractError, "seq"):
            from_dict({"schema_version": 1, "type": "strike", "t": 0})

    def test_bad_values(self):
        for kwargs in (
            {"type": "", "seq": 1, "t": 0},
            {"type": "strike", "seq": -1, "t": 0},
            {"type": "strike", "seq": True, "t": 0},
            {"type": "strike", "seq": 1, "t": float("nan")},
            {"type": "strike", "seq": 1, "t": "0"},
            {"type": "strike", "seq": 1, "t": 0, "payload": []},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ContractError):
                Envelope(**kwargs)

    def test_invalid_json(self):
        with self.assertRaises(ContractError):
            from_json("{not json")


class StrikePayloadTest(unittest.TestCase):
    def test_all_bells(self):
        for bell in range(1, 17):
            self.assertEqual(strike_payload(bell, "back", "synthetic")["bell"], bell)

    def test_rejects_bad_values(self):
        for args in ((0, "hand", "live"), (17, "hand", "live"), (1, "left", "live"), (1, "hand", "x")):
            with self.subTest(args=args), self.assertRaises(ContractError):
                strike_payload(*args)


class SequencerTest(unittest.TestCase):
    def test_increments(self):
        s = Sequencer()
        self.assertEqual([s.emit("system", 0).seq for _ in range(3)], [1, 2, 3])

    def test_producers_only_emit_known_types(self):
        with self.assertRaises(ContractError):
            Sequencer().emit("future", 0)
