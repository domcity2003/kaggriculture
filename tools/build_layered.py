"""Append a layer to a base agent and write one submittable file.

A layer shadows `agent` and delegates to the previous definition:

    _PARENT = agent
    def agent(observation, configuration=None):
        action = _PARENT(observation, configuration)
        ...                       # adjust the action
        return action

The layer can therefore change the base agent's actions without reading its
source. This concatenates a base and a layer into one main.py, keeping the
layer as a small reviewable file instead of a diff against a megabyte.

The base file's license and attribution notices sit at the top and are
preserved verbatim by concatenation.
"""
import argparse, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BANNER = """

# ---------------------------------------------------------------------------
# Layer appended below this line. Everything above is the base agent, with its
# license and attribution notices unchanged.
# ---------------------------------------------------------------------------
"""

# Kaggle executes the last callable, which need not be named `agent` in a
# base file. Capture exactly that function before adding any layer names.
PARENT_ENTRY = """
_kaggriculture_base_entry = [value for value in globals().values() if callable(value)][-1]
agent = _kaggriculture_base_entry
"""

# Rebinding an existing dictionary key does not change its insertion order.
# Reinsert the wrapper AFTER aliases/helpers so Kaggle actually executes it.
FINAL_ENTRY = """
agent = globals().pop("agent")
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--layer", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = Path(args.base).read_bytes()
    layer = Path(args.layer).read_bytes()
    out = base + BANNER.encode() + PARENT_ENTRY.encode() + layer + FINAL_ENTRY.encode()
    Path(args.out).write_bytes(out)
    print("base  %-40s %8d bytes  sha %s" % (args.base, len(base), hashlib.sha256(base).hexdigest()[:12]))
    print("layer %-40s %8d bytes" % (args.layer, len(layer)))
    print("out   %-40s %8d bytes  sha %s" % (args.out, len(out), hashlib.sha256(out).hexdigest()[:12]))


if __name__ == "__main__":
    main()
