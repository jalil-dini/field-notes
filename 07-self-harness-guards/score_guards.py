#!/usr/bin/env python3
"""Score a version of the form filler's safety guards against hand-labelled pages.

The guards are five yes/no questions put to a typed decision model (Jev) about a page, plus a threshold and an order
for each. A guard version lives in a JSON file (guards_v0.json is the one the filler shipped with). Every page in
pages.json was captured once by the filler's probe mode, so each version is judged on identical input, and nothing
is ever filled or submitted.

Run: python3 score_guards.py guards_v0.json [guards_v1.json ...]     (needs JEV_API_KEY)
"""
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SKIPS = ("sweepstakes", "excluded", "cause", "restricted", "not_offer")


def api_key():
    if os.environ.get("JEV_API_KEY"):
        return os.environ["JEV_API_KEY"]
    env = os.path.join(HERE, "..", "..", ".env")       # the bot's own key file, outside this repository
    for line in open(env):
        if line.startswith("JEV_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("Set JEV_API_KEY.")


def ask(page, guards, key, cache):
    qs = {name: {"type": "noul", "instructions": g["question"]} for name, g in guards["checks"].items()}
    ck = json.dumps([page["page"], page["fields"], qs], sort_keys=True)
    if ck in cache:
        return cache[ck]
    body = json.dumps({"model": "jev-latest", "state": {"page": page["page"], "fields": page["fields"]}, "questions": qs}).encode()
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=body, method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                answers = json.load(r)["answers"]
            break
        except Exception:
            if attempt == 2:
                raise
    cache[ck] = {k: v["noul"] for k, v in answers.items()}
    return cache[ck]


def decide(scores, guards):
    """The filler's rule: the first skip check over its threshold wins; otherwise fill if it looks like an offer."""
    for name in guards["order"]:
        g = guards["checks"][name]
        if name == "offer":
            if scores[name] < g["threshold"]:
                return "not_offer"
        elif scores[name] >= g["threshold"]:
            return name
    return "fill"


def score(guards, pages, key, cache):
    with ThreadPoolExecutor(6) as pool:
        all_scores = list(pool.map(lambda p: ask(p, guards, key, cache), pages))
    rows = []
    for p, s in zip(pages, all_scores):
        got = decide(s, guards)
        rows.append({"id": p["id"], "split": p["split"], "label": p["label"], "got": got, "scores": {k: round(v, 2) for k, v in s.items()}})
    return rows


def summary(rows):
    out = {}
    for split in ("tune", "held_out", "all"):
        r = [x for x in rows if split == "all" or x["split"] == split]
        fills_wrong = sum(x["got"] == "fill" and x["label"] != "fill" for x in r)     # the dangerous error
        skips_wrong = sum(x["got"] != "fill" and x["label"] == "fill" for x in r)     # a missed freebie
        out[split] = {"pages": len(r), "decision_right": sum((x["got"] == "fill") == (x["label"] == "fill") for x in r),
                      "reason_right": sum(x["got"] == x["label"] for x in r), "filled_when_it_should_skip": fills_wrong,
                      "skipped_a_real_offer": skips_wrong}
    return out


if __name__ == "__main__":
    pages = json.load(open(os.path.join(HERE, "pages.json")))
    cache_file = os.path.join(HERE, ".jev_cache.json")
    cache = json.load(open(cache_file)) if os.path.exists(cache_file) else {}
    key = api_key()
    results = {}
    for path in sys.argv[1:]:
        guards = json.load(open(os.path.join(HERE, path)))
        rows = score(guards, pages, key, cache)
        results[path] = {"summary": summary(rows), "rows": rows}
        s = results[path]["summary"]
        print(f"\n{path}")
        for split in ("tune", "held_out", "all"):
            x = s[split]
            print(f"  {split:9} decision {x['decision_right']:2}/{x['pages']:<2}  reason {x['reason_right']:2}/{x['pages']:<2}  "
                  f"filled-when-should-skip {x['filled_when_it_should_skip']}  skipped-real-offer {x['skipped_a_real_offer']}")
        for r in rows:
            if r["got"] != r["label"]:
                print(f"    wrong  {r['split']:8} #{r['id']:<3} label {r['label']:11} got {r['got']:11} {r['scores']}")
    json.dump(cache, open(cache_file, "w"))
    json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=1)
