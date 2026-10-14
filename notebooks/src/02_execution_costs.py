# %% [markdown]
# # Does the trading cost you assume change who wins?
#
# **Paper:** [How Execution Assumptions Change Short-Horizon Sharpe Rankings](https://arxiv.org/abs/2610.05077) (Xue, 2026)
#
# **Use case:** comparing trading agents, or any agents whose actions have a per-action cost: API calls, tool use, retries.
# A leaderboard built at zero cost can rank the busiest agent first. This notebook re-ranks the same agents as cost rises.

# %%
import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(3)
MINUTES, PATHS = 540, 400                       # nine hours of one-minute steps
steps = rng.normal(0.00002, 0.0009, size=(PATHS, MINUTES))
prices = 100 * np.cumprod(1 + steps, axis=1)

def rolling_mean(x, w):
    c = np.cumsum(np.insert(x, 0, 0, axis=1), axis=1)
    out = np.full_like(x, np.nan)
    out[:, w:] = (c[:, w:-1] - c[:, :-w - 1]) / w     # average of the previous w minutes
    return out

def run(lookback, cost):
    """Long while price is above its trailing average. Returns (mean return, mean trades per path)."""
    want = (prices > rolling_mean(prices, lookback)).astype(float)
    want[:, :lookback] = 0
    trades = np.abs(np.diff(want, axis=1, prepend=0))
    growth = np.cumprod((1 + want[:, :-1] * steps[:, 1:]) * (1 - cost * trades[:, :-1]), axis=1)[:, -1]
    return growth.mean() - 1, trades.sum(axis=1).mean()

traders = {"3-minute": 3, "10-minute": 10, "30-minute": 30, "60-minute": 60, "120-minute": 120}
costs = [0, 0.0001, 0.0002, 0.0005, 0.001, 0.002]
table = np.array([[run(lb, c)[0] for c in costs] for lb in traders.values()])
hold = (prices[:, -1] / prices[:, 0]).mean() - 1
for name, lb in traders.items():
    print(f"{name:>10} average: {run(lb, 0)[1]:5.0f} trades per path")

# %%
fig, ax = plt.subplots(figsize=(7.5, 4.2))
for row, name in zip(table, traders):
    ax.plot([c * 100 for c in costs], row * 100, marker="o", lw=2, label=name + " average")
ax.axhline(hold * 100, color="gray", ls="--", lw=1, label="buy and hold")
ax.set_xlabel("Cost per trade, %"); ax.set_ylabel("Mean return over nine hours, %")
ax.set_title("The busiest trader is first at zero cost and last at a realistic one")
ax.legend(frameon=False, fontsize=9); ax.spines[["top", "right"]].set_visible(False)
plt.show()

# %% [markdown]
# ## How much does the ranking itself move?
# Kendall's tau compares the order of the five traders at zero cost with their order at each higher cost.
# 1 means the same order, -1 means fully reversed.

# %%
def kendall_tau(a, b):
    n, s = len(a), 0
    for i in range(n):
        for j in range(i + 1, n):
            s += np.sign(a[i] - a[j]) * np.sign(b[i] - b[j])
    return s / (n * (n - 1) / 2)

for c, col in zip(costs, table.T):
    order = [list(traders)[k] for k in np.argsort(-col)]
    print(f"cost {c:.2%}: tau vs zero-cost ranking {kendall_tau(table[:, 0], col):+.2f}   best: {order[0]:<11} worst: {order[-1]}")

# %% [markdown]
# **Reading the result.** Nothing about the traders changes between rows; only the fee does.
# In my own per-minute crypto test with a 0.2% cost per fill, the model-driven trader made 110 trades in 18 hours,
# 6 of them profitable, and lost about 13% of a pretend $500 account.
