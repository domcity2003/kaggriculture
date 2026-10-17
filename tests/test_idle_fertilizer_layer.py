"""Contract tests for the single-change v10 layer, without a base agent."""
import copy
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IdleFertilizerTests(unittest.TestCase):
    def invoke(self, *, day=10, room=100, available=True, commands=None):
        commands = commands or [["PASS"], ["PASS"]]
        tile = {"kind": "PASTURE", "animal": "COW", "fertilizer_available": available}
        farm = {"farmer": [0, 0], "hands": [[0, 0]], "tiles": [[tile]]}
        private = {"shed": {"WHEAT": 100-room}, "inventories": [{}, {}]}
        obs = {"step": day*24+20, "day": day, "player": 0, "farms": [farm], "private": private}
        original = {"farmer": commands[0], "hands": commands[1:], "market": [["SELL", "MILK", 3]]}
        namespace = {"agent": lambda observation, configuration=None: copy.deepcopy(original),
                     "_r127_fields": lambda observation, action: (copy.deepcopy(farm), copy.deepcopy(private))}
        exec((ROOT/"layers/idle_fertilizer.py").read_text(), namespace)
        before = copy.deepcopy(obs)
        result = namespace["agent"](obs)
        self.assertEqual(obs, before, "layer mutated live observation")
        self.assertEqual(result["market"], original["market"])
        return result

    def test_one_collection_per_tile_and_no_extra_movement(self):
        result = self.invoke()
        self.assertEqual(result["farmer"], ["COLLECT_FERTILIZER"])
        self.assertEqual(result["hands"], [["PASS"]])

    def test_preserves_nonidle_commands(self):
        result = self.invoke(commands=[["NORTH"], ["PASS"]])
        self.assertEqual(result["farmer"], ["NORTH"])
        self.assertEqual(result["hands"], [["COLLECT_FERTILIZER"]])

    def test_does_not_collect_unavailable_or_overflowing_goods(self):
        for options in ({"available": False}, {"room": 0}, {"day": 29}):
            with self.subTest(options=options):
                result = self.invoke(**options)
                self.assertEqual(result["farmer"], ["PASS"])
                self.assertEqual(result["hands"], [["PASS"]])


if __name__ == "__main__":
    unittest.main()
