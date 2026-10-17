"""Collect otherwise-unused fertilizer during an existing worker's idle turn.

No movement, hiring, buying or sale changes. Use the base's exact field
simulator to avoid duplicating another worker's collection in this turn.
"""
_V10_PARENT = agent
_V10_REPORT = {"collections": 0}


def agent(observation, configuration=None):
    action = _V10_PARENT(observation, configuration)
    if observation["step"] == 0:
        _V10_REPORT["collections"] = 0
    if observation["day"] >= 29:
        return action
    units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
    original = observation["farms"][observation["player"]]
    positions = [original["farmer"]] + original["hands"]
    if not any(c == ["PASS"] for c in units):
        return action
    farm, private = _r127_fields(observation, action)
    # Conservative bound: even without sales, every current item fits tonight.
    room = 100-sum(private["shed"].values())-sum(sum(i.values()) for i in private["inventories"])
    if room <= 0:
        return action
    changed = False
    for i, (pos, command) in enumerate(zip(positions, units)):
        if command != ["PASS"] or room <= 0:
            continue
        tile = farm["tiles"][pos[1]][pos[0]]
        if isinstance(tile, dict) and tile.get("animal") and tile.get("fertilizer_available"):
            units[i] = ["COLLECT_FERTILIZER"]
            tile["fertilizer_available"] = False
            changed = True
            room -= 1
            _V10_REPORT["collections"] += 1
    return dict(action, farmer=units[0], hands=units[1:]) if changed else action
