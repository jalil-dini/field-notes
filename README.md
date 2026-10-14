# Field notes: papers I tested

I read new AI papers and then run a small experiment of my own on the same question.
Each folder here is one of those experiments. They are short, they run on a laptop, and
they include what went wrong.

| Demo | Paper it goes with | What it shows |
|---|---|---|
| [01-search-aware-backtest](01-search-aware-backtest) | [What survives honest evaluation?](https://arxiv.org/abs/2608.27734) | On prices with no edge at all, the best of 300 rules shows +24% in-sample and loses on held-out days. |
| [02-execution-costs](02-execution-costs) | [How Execution Assumptions Change Short-Horizon Sharpe Rankings](https://arxiv.org/abs/2610.05077) | The same three traders ranked under three fees. The ranking reverses. |
| [03-typed-decision-guardrails](03-typed-decision-guardrails) | [One Word Opens the Gate](https://arxiv.org/abs/2610.12292) | Measured scores from a typed decision model guarding a web agent, the wording change that fixed a misfire, and the one decision it still gets wrong. |
| [04-web-agent-harness](04-web-agent-harness) | [WebFovea](https://arxiv.org/abs/2610.03036) | A small form-filling agent and a local test page with the traps that broke it on real sites. |
| [05-agent-bait](05-agent-bait) | [Package Hallucination Attacks on Coding Agents through Prompt Injection in Rule Files](https://arxiv.org/abs/2610.09264) | A scan of GitHub bounty issues for traits aimed at AI agents. |

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

## Notebooks

Each demo also has a notebook that runs in Google Colab with charts and a written reading of the result.

| Notebook | Needs |
|---|---|
| [01 Search-aware backtest](notebooks/01_search_aware_backtest.ipynb) | numpy, matplotlib |
| [02 Execution costs](notebooks/02_execution_costs.ipynb) | numpy, matplotlib |
| [03 Typed decision gate](notebooks/03_typed_decision_gate.ipynb) | transformers and an open model; a GPU makes it quick |
| [04 Web agent harness](notebooks/04_web_agent_harness.ipynb) | Playwright, installed by the first cell |
| [05 Agent bait scan](notebooks/05_agent_bait_scan.ipynb) | matplotlib, network access to GitHub |

The notebooks are generated from `notebooks/src/*.py` by `tools/build_notebooks.py`.

## What these are not

- Not trading advice. The trading demos use synthetic prices, and the real results I quote came from
  pretend money. Most strategies I tested lost.
- Not benchmarks. Each is one small run, meant to make a paper's claim concrete.
- Not a claim about any named company or repository. Demo 05 reports traits, not intent.

`papers.json` holds the paper notes and the draft posts that go with each demo.
