#!/usr/bin/env python3
"""Run a notebook's code cells in order, outside Jupyter, and save each figure. Usage: run_notebook.py notebooks/x.ipynb"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
path = Path(sys.argv[1])
figs = path.parent / "figures"
figs.mkdir(exist_ok=True)
count = [0]


def save_figure(*a, **k):
    import matplotlib.pyplot as plt
    count[0] += 1
    plt.savefig(figs / ("%s-%d.png" % (path.stem, count[0])), dpi=140, bbox_inches="tight")
    plt.close("all")


scope = {"__name__": "__main__"}
for cell in json.loads(path.read_text())["cells"]:
    if cell["cell_type"] != "code":
        continue
    code = "".join(cell["source"])
    if code.lstrip().startswith(("!", "%")):
        continue                                   # shell and magic lines only make sense in Colab
    exec(compile(code, path.name, "exec"), scope)
    if "matplotlib.pyplot" in sys.modules:
        sys.modules["matplotlib.pyplot"].show = save_figure
print("ran", path.name, "- figures saved:", count[0])
