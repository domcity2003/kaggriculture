# Kaggriculture

A layer I wrote beat its own parent 52 games to 8 on my machine. On the live ladder the same change went 3 and 9. That gap is the useful result of this project, and most of the repo exists to measure it.

Kaggriculture was a two-player farm-economy simulation on Kaggle (September 2026). Each side gets $3,000 and a 10x10 farm. Over 30 in-game days (720 turns) a bot plants, waters, harvests, raises animals, hires day labour and sells into one shared market. The agent is a single function, `agent(observation, configuration) -> actions`, and the ladder updates an Elo-style rating after every win, draw or loss. I finished 1,490th of 10,148 teams (top 15%).

## What is here

| path | what it is |
|---|---|
| `planner/baseline.py` | First working agent: carrots, greedy job assignment, sell everything on the last day |
| `planner/forecast_planner.py` | Price-forecasting planner with joint worker assignment and prioritised market orders |
| `layers/` | Small wrappers that call a parent agent, adjust its action list, and fall back to the parent's answer on any error |
| `tools/evaluate.py` | Plays full seasons on fixed seeds in both seats using the official engine |
| `tools/screen_layers.py` | Runs a candidate against opponents on identical seeds and writes each result as it finishes |
| `tools/build_layered.py` | Joins a base agent and a layer into one submittable file |
| `tests/` | 19 tests: engine mechanics, layer behaviour, and the entry-point rule below |

## Results

The planner I wrote from scratch went from a rating of 175.5 (v1) to 743.6 (v7) and stopped improving around 750. Parameter search had reached a local optimum, so the remaining gains had to come from somewhere else.

Later ladder entries put my layers on top of an open-source Apache-2.0 base agent (credits in `NOTICE`), which took ratings from about 750 to about 2,600. The final pair rated 1,607 and 1,697, once most of the field was running near-identical agents.

Rating comparisons need care. The same file rated 2,610 on 21 September and 1,883 on 24 September. Two entries with identical code finished 195 points apart. As more teams ran near-identical strong agents, about 23% of my games became draws against copies of the same code. The fall from 2,621 to about 1,700 mostly reflects the field changing, not later versions being worse.

## The finding: mirror matches reward almost any change

Two identical agents try to sell the same item on the same turn. The market recovers only one or two units per turn, so the second seller gets almost nothing. Any change that sells slightly earlier wins the mirror, whether or not it helps against anyone else.

`idle_fertilizer` showed this: 52-8 against its own parent locally, 3-9 on the ladder (rating 2,346 against the parent's 2,610). I withdrew it.

The one layer that held up on the ladder is `preempt_produce`. It sells valuable produce (melon, wool, milk, strawberry) once 12 or more units sit in storage, instead of waiting. Against a near-identical opponent it turned a 2-22 record into 22-2, and the threshold barely matters (k=8, 10 and 12 tied at 54-10 on fresh seeds). The mechanism is a first-mover advantage in a shared-resource game, and I confirmed it in a replay rather than inferring it from win counts.

## How I decided what to submit

1. **Paired foreign test.** Run the candidate and the unmodified base on identical seeds, both seats, against the same outside opponents, at least 24 games per cell. Compare per-game differences, not pooled win rates.
2. **Placebo arm.** Run a layer that does nothing. If the placebo does not track the base, the test is measuring noise.
3. **Seed-level error bars.** Game-level bars treated correlated games as independent and were overconfident.
4. **Fresh holdout seeds** for final confirmation, and never compare runs from different seed blocks. One early ledger entry claimed an improvement against every opponent; re-running the old version on the same seeds reversed one of three comparisons.
5. **One change per submission,** so a result can be explained afterwards.

## Smaller findings from the planner phase

- In a replay against a strong opponent, 57% of my workers' actions were walking, against 42% for theirs. Distance-aware job assignment, commitment to a job, and joint assignment moved the rating from 620.9 (v2) to 743.6 (v7).
- Melons are a trap in a contested market. Price falls quadratically with supply, and a change that pulled labour toward melons went 0-6 against its parent.
- Idle land turned out to be a labour problem. A fix that filled idle tiles never fired, because the planner had already assigned a crop to every tile.

## Engine facts that cost me submissions

- Kaggle runs the **last callable in the file**, not the one named `agent`. An early build silently ran the base agent and ignored my layer, and an equivalence test could not catch it. `tests/test_layered_entrypoint.py` checks that the wrapper actually executes.
- A new plant dies overnight unless watered that day.
- The final (720th) state has no overnight deposit, so the last turn needs an explicit sell.
- Market price changes per unit sold, so quoted price times quantity overstates revenue.
- Too many simultaneous PLANT requests for one crop reject the whole batch.

## Running it

```bash
pip install -r requirements.txt
python -m unittest discover -s tests
python tools/evaluate.py --agent planner/forecast_planner.py --seeds 20
```

The engine is the official `kaggle-environments` package (pinned in `requirements.txt`). Layers are appended to a base agent with `tools/build_layered.py --base <agent.py> --layer layers/preempt_produce.py --out main.py`.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
