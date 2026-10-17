"""Behaviour of the preempt_produce layer in isolation, without the 1MB parent."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYER = ROOT / "layers" / "preempt_produce.py"


def load(parent):
    """Execute the layer source with `agent` pre-bound to `parent`."""
    namespace = {"agent": parent}
    exec(compile(LAYER.read_text(), str(LAYER), "exec"), namespace)
    return namespace["agent"]


def observation(shed, step=100):
    return {"step": step, "private": {"shed": dict(shed)}}


class PreemptProduceLayer(unittest.TestCase):
    def test_sells_held_produce_above_threshold(self):
        agent = load(lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [], "market": []})
        action = agent(observation({"MELON": 20}))
        self.assertEqual(action["market"], [["SELL", "MELON", 20]])

    def test_leaves_holdings_below_threshold_alone(self):
        agent = load(lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [], "market": []})
        self.assertEqual(agent(observation({"MELON": 11}))["market"], [])

    def test_never_sells_wheat_or_fertilizer(self):
        agent = load(lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [], "market": []})
        action = agent(observation({"WHEAT": 90, "FERTILIZER": 90}))
        self.assertEqual(action["market"], [])

    def test_subtracts_quantities_the_parent_already_sells(self):
        parent = lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [],
                                        "market": [["SELL", "WOOL", 15]]}
        action = load(parent)(observation({"WOOL": 20}))
        self.assertEqual(action["market"], [["SELL", "WOOL", 15], ["SELL", "WOOL", 5]])

    def test_subtracts_same_step_pickups(self):
        parent = lambda obs, cfg=None: {"farmer": ["PICKUP", "MILK", 6], "hands": [],
                                        "market": []}
        self.assertEqual(load(parent)(observation({"MILK": 18}))["market"],
                         [["SELL", "MILK", 12]])

    def test_appends_rather_than_reordering(self):
        """The base agent engineers its market indices; existing ones must not move."""
        existing = [["BUY_PRODUCT", "WHEAT", 4], [], ["HIRE"]]
        parent = lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [],
                                        "market": [list(o) for o in existing]}
        action = load(parent)(observation({"STRAWBERRY": 30}))
        self.assertEqual(action["market"][:3], existing)

    def test_respects_the_ten_order_cap(self):
        full = [["SELL", "CARROT", 1]] * 10
        parent = lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [], "market": full}
        self.assertEqual(load(parent)(observation({"MELON": 40}))["market"], full)

    def test_uses_last_order_slot_for_more_valuable_surplus(self):
        existing = [["HIRE"]] * 9
        parent = lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [],
                                        "market": existing}
        obs = observation({"MELON": 20, "MILK": 20})
        obs["market"] = {"prices": {"MELON": 40, "MILK": 160}}
        market = load(parent)(obs)["market"]
        self.assertEqual(len(market), 10)
        self.assertEqual(market[:9], existing)
        self.assertEqual(market[9], ["SELL", "MILK", 20])

    def test_leaves_the_parent_action_object_untouched(self):
        original = {"farmer": ["PASS"], "hands": [], "market": []}
        load(lambda obs, cfg=None: original)(observation({"MELON": 20}))
        self.assertEqual(original["market"], [])

    def test_a_parent_failure_mode_cannot_break_the_turn(self):
        agent = load(lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [], "market": None})
        self.assertIn("farmer", agent(observation({"MELON": 20})))


if __name__ == "__main__":
    unittest.main()
