#!/usr/bin/env python3
"""What do public agent skill files ask an agent to do?

Agent skills are files of plain-language instructions (usually SKILL.md) that an AI agent loads and follows with
the user's privileges. This script pulls a sample of public SKILL.md files from GitHub and counts instructions that
deserve review before an agent follows them: piping a download into a shell, using sudo, touching credentials,
telling the agent not to ask or not to tell, skipping permission prompts, installing unpinned packages.

A match is a capability that needs a human look, not evidence of bad intent. Plenty of honest install skills use sudo.

Related reading: arXiv:2609.07360 (configuration exposures in AI coding-agent supply chains) and
arXiv:2606.23416 (detecting malicious agent skills in the wild).
Needs a GitHub token for code search: set GITHUB_TOKEN, or have the gh CLI logged in.
Run: python3 scan_skills.py [number of files, default 300]
"""
import base64
import collections
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

LIMIT = int(next((a for a in sys.argv[1:] if a.isdigit()), 300))
CHECKS = {
    "pre-approves shell access (allowed-tools: Bash)": r"(?m)^allowed-tools:.*\bBash\b",
    "handles API keys or other credentials": r"~/\.ssh|id_rsa|~/\.aws|\.aws/credentials|keychain|\.netrc|printenv|\$\{?[A-Z_]*(API_KEY|TOKEN|SECRET)\b",
    "POSTs data to an outside server": r"(curl\s[^\n]*-(X\s*POST|d\s|-data)|requests\.post\(|fetch\([^)]*method:\s*['\"]POST)(?![^\n]*(localhost|127\.0\.0\.1))",
    "mentions sudo": r"\bsudo\s+\w",
    "pipes a download into a shell": r"(curl|wget)[^\n|]{0,200}\|\s*(sudo\s+)?(ba|z)?sh\b",
    "runs an agent with permission prompts off": r"dangerously-skip-permissions|bypassPermissions|--yolo\b",
    "installs an unpinned package": r"\b(npx\s+-y\s+[@\w/-]+(?!@\d)|uvx\s+[\w-]+(?!==))",
    "tells the agent to hide something from the user": r"(do not|don'?t|never) (tell|inform|mention (it |this )?to|show) the user|without (telling|informing|notifying) the user|hide (this|it) from the user",
    "overrides earlier instructions": r"ignore (all |any )?(previous|prior|above|other) instructions",
}


def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()


def api(path, tok):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json", "User-Agent": "skill-scan-demo"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    tok = token()
    if not tok:
        sys.exit("Set GITHUB_TOKEN or log in with the gh CLI; GitHub code search needs a token.")
    found = []
    for page in range(1, LIMIT // 100 + 2):
        items = api("/search/code?" + urllib.parse.urlencode({"q": "filename:SKILL.md", "per_page": 100, "page": page}), tok)["items"]
        found += [(i["repository"]["full_name"], i["path"]) for i in items]
        if len(items) < 100 or len(found) >= LIMIT:
            break
        time.sleep(7)                      # code search allows about 10 requests a minute
    found = list(dict.fromkeys(found))[:LIMIT]
    hits, per_repo, read, any_file, samples = collections.Counter(), collections.defaultdict(set), 0, 0, collections.defaultdict(list)
    for repo, path in found:
        try:
            body = base64.b64decode(api("/repos/%s/contents/%s" % (repo, urllib.parse.quote(path)), tok)["content"]).decode("utf-8", "replace")
        except Exception:
            continue
        read += 1
        matched = False
        for name, pattern in CHECKS.items():
            m = re.search(pattern, body, re.I)
            if m:
                matched = True
                hits[name] += 1
                per_repo[name].add(repo)
                line = body[max(0, body.rfind("\n", 0, m.start()) + 1):body.find("\n", m.end()) if body.find("\n", m.end()) > 0 else m.end()]
                samples[name].append(line.strip()[:160])
        any_file += matched
    flagged_any = len(set().union(*per_repo.values())) if per_repo else 0
    result = {"files_read": read, "files_with_any_flag": any_file, "repos_with_any_flag": flagged_any, "checks": {k: hits.get(k, 0) for k in CHECKS}}
    print("%d public SKILL.md files read" % read)
    for name in CHECKS:
        print("  %-44s %4d files (%4.1f%%)" % (name, hits.get(name, 0), 100 * hits.get(name, 0) / max(read, 1)))
    print("  %-44s %4d files (%4.1f%%)" % ("any of the above", any_file, 100 * any_file / max(read, 1)))
    if "--show" in sys.argv:                 # the matched lines, for checking the patterns by eye (no file names)
        for name, lines in samples.items():
            print("\n" + name)
            for line in lines[:6]:
                print("   ", line)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_scan.json"), "w") as f:
        json.dump(result, f, indent=1)


if __name__ == "__main__":
    main()
