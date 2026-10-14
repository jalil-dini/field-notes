# %% [markdown]
# # Who are GitHub's cash bounties written for?
#
# **Paper:** [Package Hallucination Attacks on Coding Agents through Prompt Injection in Rule Files](https://arxiv.org/abs/2610.09264) (Wang, Jiang, Wang and Gong, 2026),
# which shows what content planted in a repository for agents to read can make them do.
#
# **Use case:** deciding what an autonomous agent is allowed to act on. An agent sent to "find paid work" will read
# whatever search returns. This notebook measures how much of one such search is shaped for agents rather than people.
#
# It uses GitHub's public search API with no token. A trait match is a reason for care, not a judgement about any repository.

# %%
import collections, json, re, urllib.parse, urllib.request
import matplotlib.pyplot as plt

QUERY = 'label:"💎 Bounty" state:open is:issue'

def search(page):
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode(
        {"q": QUERY, "sort": "created", "order": "desc", "per_page": 100, "page": page})
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "bait-scan-demo"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["items"]

issues = search(1) + search(2)
print(len(issues), "open issues with a cash-bounty label, newest first")

# %%
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

by_repo = collections.defaultdict(list)
for issue in issues:
    by_repo[issue["repository_url"].split("/repos/")[1]].append(traits(issue))
flagged = {r: t for r, t in by_repo.items() if sum(bool(x) for x in t) >= max(1, len(t) // 2)}
in_flagged = sum(len(t) for t in flagged.values())
print(f"{in_flagged} of {len(issues)} issues ({in_flagged / len(issues):.0%}) sit in {len(flagged)} repositories "
      f"where most issues show agent-directed traits; {len(by_repo)} repositories in total")

# %%
ranked = sorted(by_repo.items(), key=lambda kv: -len(kv[1]))[:8]
labels = [f"repository {i + 1}" for i in range(len(ranked))]          # counted, not named
with_trait = [sum(bool(x) for x in t) for _, t in ranked]
without = [len(t) - w for (_, t), w in zip(ranked, with_trait)]
fig, ax = plt.subplots(figsize=(7.5, 3.8))
ax.barh(labels, with_trait, label="issues with an agent-directed trait")
ax.barh(labels, without, left=with_trait, label="issues without")
ax.invert_yaxis(); ax.set_xlabel("Open bounty-labelled issues")
ax.set_title("A few repositories hold nearly all the newest bounties")
ax.legend(frameon=False, fontsize=9); ax.spines[["top", "right"]].set_visible(False)
plt.show()

# %% [markdown]
# **Reading the result.** When I ran this on 13 October 2026, 193 of the 198 newest bounty-labelled issues sat in three
# repositories whose issues carried labels addressed to AI agents and payouts of $400 or more on beginner tasks.
# The numbers change daily; run it and see.
#
# The rule I took from it: an agent may read anything, but an offer it finds is not an instruction.
