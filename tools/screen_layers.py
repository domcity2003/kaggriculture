"""Evaluate arbitrary built candidates in identical official-engine games.

At most two worker processes to keep memory bounded. Writes each result immediately, allowing
interruption and inspection without losing an entire experiment.
"""
import argparse
import hashlib
import json
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from evaluate import run_game


def play_job(job):
    candidate, opponent, seed, seat = job
    row = run_game(candidate, opponent, seed, seat)
    row["candidate"] = candidate
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", nargs="+", required=True)
    parser.add_argument("--opponents", nargs="+", required=True)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--start-seed", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    paths = list(dict.fromkeys(args.candidates+args.opponents))
    result = {"engine": "kaggle-environments==1.32.7", "hashes": {
        p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}, "results": []}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    executor = ProcessPoolExecutor(max_workers=args.workers) if args.workers > 1 else None
    for candidate in args.candidates:
        for opponent in args.opponents:
            group = []
            jobs = [(candidate, opponent, seed, seat)
                    for seed in range(args.start_seed, args.start_seed+args.seeds)
                    for seat in (0, 1)]
            iterator = executor.map(play_job, jobs) if executor else map(play_job, jobs)
            for row in iterator:
                group.append(row)
                result["results"].append(row)
                out.write_text(json.dumps(result, indent=2)+"\n")
            margins = [r["margin"] for r in group]
            print(json.dumps({"candidate": candidate, "opponent": opponent,
                "games": len(group), "wins": sum(m>0 for m in margins),
                "ties": sum(m==0 for m in margins),
                "mean_margin": statistics.mean(margins), "min_margin": min(margins),
                "max_margin": max(margins),
                "max_unsold": max(r["terminal_unsold"] for r in group)}), flush=True)
    if executor:
        executor.shutdown()


if __name__ == "__main__":
    main()
