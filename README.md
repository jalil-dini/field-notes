# Field notes: papers I tested

I read new AI papers and then run a small experiment of my own on the same question.
Each folder here is one of those experiments. They are short, they run on a laptop, and
they include what went wrong.

| Demo | Paper it goes with | What it shows |
|---|---|---|
| [01-search-aware-backtest](01-search-aware-backtest) | [What survives honest evaluation?](https://arxiv.org/abs/2608.27734) | On prices with no edge at all, the best of 300 rules shows +24% in-sample and loses on held-out days. |
| [02-execution-costs](02-execution-costs) | [How Execution Assumptions Change Short-Horizon Sharpe Rankings](https://arxiv.org/abs/2610.05077), [Can AI Make Money in Crypto?](https://arxiv.org/abs/2609.34510) | The same three traders ranked under three fees. The ranking reverses. |
| [03-typed-decision-guardrails](03-typed-decision-guardrails) | [One Word Opens the Gate](https://arxiv.org/abs/2610.12292) | Measured scores from a typed decision model guarding a web agent, the wording change that fixed a misfire, and the one decision it still gets wrong. |
| [04-web-agent-harness](04-web-agent-harness) | [WebFovea](https://arxiv.org/abs/2610.03036) | A small form-filling agent and a local test page with the traps that broke it on real sites. |
| [05-agent-bait](05-agent-bait) | [An Exploration of Attacks on AI Agent Systems](https://arxiv.org/abs/2610.12524) | A scan of GitHub bounty issues for traits aimed at AI agents. |

## Running them

Demos 01, 02, 03 and 05 need only Python 3:

```sh
python3 01-search-aware-backtest/best_of_n.py
python3 02-execution-costs/cost_flip.py
python3 03-typed-decision-guardrails/guard_table.py
python3 05-agent-bait/bait_scan.py     # calls GitHub's public search API
```

Demo 04 needs Node 20+, Playwright's Chromium, and a TypeSafe AI key:

```sh
cd 04-web-agent-harness
npm install && npx playwright install chromium
TYPESAFE_API_KEY=... node form_agent.js "file://$PWD/tricky_form.html"
```

It fills the test form as the fictional person in `profile.example.json`. Add `--dry` to fill without
submitting, or `--probe` to print only the guard scores. Point it at real websites with care: it submits.

## What these are not

- Not trading advice. The trading demos use synthetic prices, and the real results I quote came from
  pretend money. Most strategies I tested lost.
- Not benchmarks. Each is one small run, meant to make a paper's claim concrete.
- Not a claim about any named company or repository. Demo 05 reports traits, not intent.

`papers.json` holds the paper notes and the draft posts that go with each demo.
