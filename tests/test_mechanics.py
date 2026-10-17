"""Regression checks for costly timing assumptions using the official engine."""
import contextlib
import io
import unittest

with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from kaggle_environments import make


def action(op=None, market=None):
    return {"farmer": op or ["PASS"], "hands": [], "market": market or []}


class MechanicsTests(unittest.TestCase):
    def test_bought_seeds_only_usable_next_turn(self):
        env = make("kaggriculture", configuration={"seed": 0})
        env.step([action(["PLANT", "CARROT"], [["BUY_SEED", "CARROT", 1]]), action()])
        obs = env.state[0].observation
        self.assertIsNone(obs.farms[0]["tiles"][4][4])
        env.step([action(["PLANT", "CARROT"]), action()])
        self.assertEqual(env.state[0].observation.farms[0]["tiles"][4][4]["kind"], "PLANT")

    def test_new_plant_dies_if_not_watered_same_day(self):
        env = make("kaggriculture", configuration={"seed": 0})
        env.step([action(market=[["BUY_SEED", "CARROT", 1]]), action()])
        env.step([action(["PLANT", "CARROT"]), action()])
        while env.state[0].observation.day == 0:
            env.step([action(), action()])
        self.assertEqual(env.state[0].observation.farms[0]["tiles"][4][4]["kind"], "WEED")

    def test_drop_can_be_sold_same_turn(self):
        env = make("kaggriculture", configuration={"seed": 0})
        env.state[0].observation.private["inventories"][0]["CARROT"] = 3
        env.step([action(["DROP"], [["SELL", "CARROT", 100]]), action()])
        self.assertGreater(env.state[0].observation.farms[0]["money"], 3000)
        self.assertEqual(env.state[0].observation.private["shed"]["CARROT"], 0)

    def test_season_ends_before_final_overnight_deposit(self):
        env = make("kaggriculture", configuration={"seed": 0})
        env.run(["pass", "pass"])
        self.assertEqual(len(env.steps), 720)
        self.assertEqual(env.steps[-2][0].observation.hour, 22)
        self.assertEqual(env.state[0].observation.hour, 23)
        self.assertEqual([s.reward for s in env.state], [3000, 3000])


if __name__ == "__main__":
    unittest.main()
