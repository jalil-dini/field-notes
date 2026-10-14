#!/usr/bin/env python3
"""A typed decision model as an agent guardrail: what it got right, and how wording moved it.

A typed decision model returns a probability over options you define and writes no text. We put one in
front of a form-filling agent and asked five yes/no questions about each page before the agent could type.
This prints our measurements and marks which decisions were right.

Related reading: arXiv:2610.12292 ("One Word Opens the Gate"), which attacks this kind of gate by renaming
its options. Our case is the friendly version of the same effect: nobody attacked it, and rewording one
question still moved the score on the same pages from the high 50s to single digits.
Standard library only. Run: python3 guard_table.py
"""
import json
from pathlib import Path

LIMITS = {"sweepstakes": 70, "cause": 40, "restricted": 50, "excluded": 60}   # refuse at or above
MIN_OFFER = 50                                                               # refuse below

data = json.loads((Path(__file__).parent / "measurements.json").read_text())
before = data["before_rewording"]
print("Before rewording, the sweepstakes question scored ordinary free-sticker forms just over the %d cutoff:" % before["threshold"])
for page, score in before["scores"].items():
    print("  %-22s %d  -> refused, wrongly" % (page, score))

print("\nAfter rewording:")
print("  %-34s %6s %6s %6s %6s %6s   %-8s %s" % ("page", "offer", "sweep", "cause", "restr", "excl", "gate", "correct?"))
wrong = 0
for row in data["after_rewording"]["pages"]:
    refuse = row["offer"] < MIN_OFFER or any(row[k] >= v for k, v in LIMITS.items())
    right = refuse == (row["kind"] == "must refuse")
    wrong += not right
    star = "*" if row["sweepstakes_measured_with"] != "new wording" else " "
    print("  %-34s %6d %5d%s %6d %6d %6d   %-8s %s" % (row["page"], row["offer"], row["sweepstakes"], star, row["cause"], row["restricted"],
                                                     row["excluded"], "refuse" if refuse else "allow", "yes" if right else "NO (blocked a page it could have filled)"))
print("  * sweepstakes column measured before that question was reworded")
print("\n%d of %d decisions wrong. The one miss fails closed: it blocks a harmless page." % (wrong, len(data["after_rewording"]["pages"])))
print("\nWhat it cost to learn where the gaps were:")
for line in data["incidents_before_each_guard_existed"]:
    print("  -", line)
