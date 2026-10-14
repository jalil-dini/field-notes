#!/usr/bin/env python3
"""Turn notebooks/src/*.py (cells split by "# %%" and "# %% [markdown]") into Colab-ready .ipynb files."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for src in sorted((ROOT / "notebooks" / "src").glob("*.py")):
    cells = []
    for block in re.split(r"(?m)^# %%", src.read_text())[1:]:
        head, _, body = block.partition("\n")
        body = body.strip("\n")
        if "[markdown]" in head:
            text = "\n".join(line[2:] if line.startswith("# ") else line.lstrip("#") for line in body.splitlines())
            cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)})
        else:
            cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": body.splitlines(keepends=True)})
    nb = {"cells": cells, "metadata": {"colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"},
                                       "language_info": {"name": "python"}, "accelerator": "GPU" if "transformers" in src.read_text() else None},
          "nbformat": 4, "nbformat_minor": 5}
    out = ROOT / "notebooks" / (src.stem + ".ipynb")
    out.write_text(json.dumps(nb, indent=1))
    print("built", out.name, len(cells), "cells")
