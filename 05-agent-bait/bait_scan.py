#!/usr/bin/env python3
"""Where do "bounties" for AI agents come from?

Searches GitHub for open issues carrying a cash-bounty label and counts how many show traits aimed at
autonomous agents rather than people: labels that address agents directly, large payouts on "good first
issue" tasks, and comment threads far longer than a real bounty attracts.

We ran into this while looking for paid open-source work an agent could do. Most of what search returned
was concentrated in a few repositories with these traits. A trait match is a reason to be careful, not proof
of anything about a repository.

Related reading: arXiv:2610.12524 (attacks on AI agent systems) and arXiv:2610.09264 (prompt injection
through files a coding agent trusts).
Standard library only; uses GitHub's public search API (no token, about 10 searches a minute).
Run: python3 bait_scan.py
"""
import collections
import json
import re
import urllib.parse
import urllib.request

QUERY = 'label:"💎 Bounty" state:open is:issue'


def search(page):
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode({"q": QUERY, "sort": "created", "order": "desc", "per_page": 100, "page": page})
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "bait-scan-demo"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["items"]


def traits(issue):
    labels = [l["name"].lower() for l in issue["labels"]]
    amounts = [float(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
               for l in labels for m in [re.fullmatch(r"\$([\d,.]+)(k)?", l)] if m]
    found = []
    if any("agent" in l for l in labels):
        found.append("label addresses AI agents")
    if amounts and max(amounts) >= 400 and "good first issue" in labels:
        found.append("large payout on a beginner task")
    if issue["comments"] >= 100:
        found.append("100+ comments")
    return found


def main():
    issues = search(1) + search(2)
    by_repo = collections.defaultdict(list)
    for issue in issues:
        by_repo[issue["repository_url"].split("/repos/")[1]].append(traits(issue))
    flagged = {r: t for r, t in by_repo.items() if sum(bool(x) for x in t) >= max(1, len(t) // 2)}
    in_flagged = sum(len(t) for t in flagged.values())
    print("%d open bounty-labelled issues in %d repositories (newest first)" % (len(issues), len(by_repo)))
    print("%d of those issues (%d%%) sit in %d repositories where most issues show agent-bait traits"
          % (in_flagged, 100 * in_flagged / max(len(issues), 1), len(flagged)))
    counts = collections.Counter(x for t in by_repo.values() for issue_traits in t for x in issue_traits)
    for name, n in counts.most_common():
        print("  %-34s %d issues" % (name, n))
    print("\nRepositories with the most bounty-labelled issues:")
    for repo, t in sorted(by_repo.items(), key=lambda kv: -len(kv[1]))[:8]:
        print("  %-44s %3d issues, %3d with a trait" % (repo[:44], len(t), sum(bool(x) for x in t)))


if __name__ == "__main__":
    main()
