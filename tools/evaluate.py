"""Sequential, reproducible official-engine evaluation; bounded memory.

Usage: python tools/evaluate.py --agent main.py --seeds 20
"""
import argparse
import contextlib
import hashlib
import io
import json
import random
import statistics
import time
from pathlib import Path

with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    import kaggle_environments
    from kaggle_environments import make


def run_game(candidate, opponent, seed, seat, replay=None):
    random.seed(seed)  # built-in random agent uses global random, not env seed
    env = make("kaggriculture", configuration={"seed": seed})
    pair = [opponent, opponent]
    pair[seat] = candidate
    start = time.perf_counter()
    env.run(pair)
    elapsed = time.perf_counter() - start
    statuses = [s.status for s in env.state]
    if len(env.steps) != 720 or statuses != ["DONE", "DONE"]:
        raise RuntimeError(f"Incomplete game: {len(env.steps)} states, {statuses}")
    errors = [log for turn in env.logs for log in turn if log.get("stderr")]
    if errors:
        raise RuntimeError(f"Agent stderr: {errors[:2]}")
    cash = [s.reward for s in env.state]
    for i, state in enumerate(env.state):
        if cash[i] != state.observation.farms[i]["money"]:
            raise AssertionError("Reward does not match final bank")
    private = env.state[seat].observation.private
    record = {"seed": seed, "seat": seat, "opponent": opponent,
              "cash": cash[seat], "opponent_cash": cash[1-seat],
              "margin": cash[seat]-cash[1-seat], "seconds": round(elapsed, 3),
              "terminal_unsold": sum(private["shed"].values()) +
                  sum(sum(inv.values()) for inv in private["inventories"]),
              "terminal_seeds": sum(private["seeds"].values())}
    if replay:
        Path(replay).write_text(json.dumps(env.toJSON()))
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="main.py")
    parser.add_argument("--opponents", nargs="+", default=["pass", "random", "starter"])
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--start-seed", type=int, default=0)
    parser.add_argument("--output", default="results/baseline.json")
    parser.add_argument("--replay")
    args = parser.parse_args()
    rows = []
    for opponent in args.opponents:
        for seed in range(args.start_seed, args.start_seed + args.seeds):
            for seat in (0, 1):
                row = run_game(args.agent, opponent, seed, seat,
                               args.replay if not rows else None)
                rows.append(row)
        group = [r for r in rows if r["opponent"] == opponent]
        margins = [r["margin"] for r in group]
        print(json.dumps({"opponent": opponent, "games": len(group),
            "wins": sum(m > 0 for m in margins), "ties": sum(m == 0 for m in margins),
            "mean_cash": statistics.mean(r["cash"] for r in group),
            "mean_margin": statistics.mean(margins), "min_margin": min(margins),
            "max_margin": max(margins),
            "max_unsold": max(r["terminal_unsold"] for r in group)}), flush=True)
    output = Path(args.output)
    output.parent.mkdir(exist_ok=True, parents=True)
    output.write_text(json.dumps({"engine": kaggle_environments.__version__,
        "agent": args.agent,
        "sha256": hashlib.sha256(Path(args.agent).read_bytes()).hexdigest(),
        "results": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
