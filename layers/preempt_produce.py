"""Sell idle produce the parent is sitting on, rather than waiting for the price.

Mechanism: market inventory only drains by one or two units per town tick
(the engine's town-consumption step), so a glutted price
recovers very slowly. Holding stock therefore earns almost nothing, while in a
mirror match the opponent's identical policy eventually dumps the same item and
takes the uncrashed price first. Selling held produce now trades the tiny
recovery for first-strike pricing.

Restricted to the four pure-sale products. WHEAT is animal feed and FERTILIZER
is crop input; selling either was already measured as a large loss
(measured in an earlier sweep).

Threshold: 12 units held.
"""
_V11_ITEMS = ("MELON", "WOOL", "MILK", "STRAWBERRY")
_V11_MIN = 12
_V11_PARENT = agent
_V11_REPORT = {"orders": 0, "units": 0}


def agent(observation, configuration=None):
    action = _V11_PARENT(observation, configuration)
    if observation["step"] == 0:
        _V11_REPORT["orders"] = 0
        _V11_REPORT["units"] = 0
    try:
        market = list(action.get("market") or [])
        if len(market) >= 10:
            return action
        shed = observation["private"]["shed"] or {}
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        extra = []
        for item in _V11_ITEMS:
            held = int(shed.get(item, 0))
            if held < _V11_MIN:
                continue
            taken = sum(int(c[2]) for c in units
                        if c and c[0] == "PICKUP" and len(c) >= 3 and c[1] == item)
            scheduled = sum(int(o[2]) for o in market
                            if len(o) >= 3 and o[0] == "SELL" and o[1] == item)
            surplus = held - taken - scheduled
            if surplus <= 0:
                continue
            extra.append(["SELL", item, surplus])
        if not extra:
            return action
        slots = 10 - len(market)
        if len(extra) > slots:
            prices = (observation.get("market") or {}).get("prices") or {}
            extra = sorted(extra, key=lambda order:
                           float(prices.get(order[1], 0)) * order[2], reverse=True)[:slots]
        _V11_REPORT["orders"] += len(extra)
        _V11_REPORT["units"] += sum(order[2] for order in extra)
        return dict(action, market=market + extra)
    except Exception:
        return action
