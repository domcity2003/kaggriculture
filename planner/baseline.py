"""Baseline v1: coordinated carrot farming on the starting quadrant.

No persistent state or external dependencies. Intended as a reliable ladder
baseline, not an optimized economic policy.
"""


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _move(pos, target):
    if pos[0] != target[0]:
        return ["EAST" if pos[0] < target[0] else "WEST"]
    if pos[1] != target[1]:
        return ["SOUTH" if pos[1] < target[1] else "NORTH"]
    return ["PASS"]


def agent(obs, configuration=None):
    cfg = configuration or {}
    farm = obs["farms"][obs["player"]]
    private = obs["private"]
    tiles = farm["tiles"]
    size = len(tiles)
    half = size // 2
    access = [(half - 1, half - 1), (half, half - 1),
              (half - 1, half), (half, half)]
    day, hour = obs["day"], obs["hour"]
    turns = cfg.get("turnsPerDay", 24)
    final_step = cfg.get("episodeSteps", 720) - 2
    step = obs.get("step", day * turns + hour)
    final_day = final_step // turns
    remaining = final_step - step + 1
    seed_count = private["seeds"].get("CARROT", 0)
    can_plant = day + 3 <= final_day
    positions = [farm["farmer"]] + list(farm["hands"])
    inventories = private["inventories"]
    jobs = []
    empty = 0
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            pos = (x, y)
            if tile is None:
                empty += 1
                if can_plant:
                    jobs.append((pos, ["PLANT", "CARROT"], 20))
            elif isinstance(tile, dict):
                if tile.get("kind") == "WEED" and can_plant:
                    jobs.append((pos, ["DIG"], 10))
                elif tile.get("kind") == "PLANT":
                    age = day - tile["planted_day"]
                    harvest = age >= 3 or (day == final_day and age >= 2)
                    if not tile["watered_today"]:
                        urgent = tile["consecutive_unwatered"] >= 1
                        jobs.append((pos, ["WATER"], 100 if urgent else 50))
                    elif harvest:
                        jobs.append((pos, ["HARVEST"], 80))

    actions = []
    reserved = set()
    for i, pos in enumerate(positions):
        inv = inventories[i] if i < len(inventories) else {}
        target_shed = min(access, key=lambda p: _distance(pos, p))
        to_shed = _distance(pos, target_shed)
        carrying = sum(inv.values()) > 0
        # Last-day inventories never reach another automatic overnight drop.
        if carrying and day == final_day and remaining <= to_shed + 3:
            actions.append(["DROP"] if to_shed == 0 else _move(pos, target_shed))
            continue
        candidates = []
        for target, op, value in jobs:
            if target in reserved:
                continue
            distance = _distance(pos, target)
            if op[0] == "PLANT":
                if seed_count <= 0 or hour + distance + 2 >= turns:
                    continue
            if hour + distance >= turns:
                continue
            if day == final_day:
                home = min(_distance(target, p) for p in access)
                # WATER may need a subsequent HARVEST, then travel and DROP.
                work = 2 if op[0] == "WATER" else 1
                if distance + work + home + 1 > remaining:
                    continue
            candidates.append((value / (distance + 1), -distance, target, op))
        if candidates:
            _, _, target, op = max(candidates)
            reserved.add(target)
            if op[0] == "PLANT":
                seed_count -= 1  # reserve seeds, including workers en route
            actions.append(op if tuple(pos) == target else _move(pos, target))
        elif carrying and (day == final_day or to_shed == 0):
            actions.append(["DROP"] if to_shed == 0 else _move(pos, target_shed))
        else:
            actions.append(["PASS"])

    # Field actions happen before market orders, so this also sells same-turn
    # DROP deposits. Oversized SELL simply stops when the shed is empty.
    market = [["SELL", "CARROT", 100]]
    if can_plant and hour < turns - 3:
        needed = max(0, empty - private["seeds"].get("CARROT", 0))
        affordable = max(0, int((farm["money"] - 20) // 20))
        if needed and affordable:
            market.append(["BUY_SEED", "CARROT", min(needed, affordable)])
    if hour <= 1 and jobs:
        market.extend([["HIRE"] for _ in range(max(0, 6 - len(farm["hands"])))])
    return {"farmer": actions[0], "hands": actions[1:],
            "market": market[:cfg.get("maxMarketOrdersPerTurn", 10)]}
