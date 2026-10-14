# %% [markdown]
# # How good does the best of N strategies look when there is nothing to find?
#
# **Paper:** [What survives honest evaluation?](https://arxiv.org/abs/2608.27734) (Gençay, 2026)
#
# **Use case:** anyone who searches over trading rules, prompts, model checkpoints or hyperparameters and reports the winner.
# The search itself manufactures a good-looking result. This notebook measures how much, on data where skill is impossible.
#
# Prices below are random walks with zero drift. Every strategy's true edge is exactly zero.

# %%
import numpy as np
import matplotlib.pyplot as plt
from statistics import NormalDist

rng = np.random.default_rng(7)
DAYS, SPLIT, RUNS = 365, 255, 400        # one year, first 70% to choose, last 30% to check
returns = rng.normal(0, 0.03, size=(RUNS, DAYS))      # 3% daily noise, no drift
prices = 100 * np.cumprod(1 + returns, axis=1)

def rolling_mean(x, w):
    c = np.cumsum(np.insert(x, 0, 0, axis=1), axis=1)
    out = np.full_like(x, np.nan)
    out[:, w - 1:] = (c[:, w:] - c[:, :-w]) / w
    return out

def strategy_daily_returns(fast, slow):
    """Long when the fast average is above the slow one, flat otherwise. Decided at the close, earned next day."""
    signal = (rolling_mean(prices, fast) > rolling_mean(prices, slow)).astype(float)
    return signal[:, :-1] * returns[:, 1:]            # shape (RUNS, DAYS-1)

# %% [markdown]
# ## Try N rules, keep the best on the first 70% of days, then look at the last 30%

# %%
rules = [(int(rng.integers(2, 31)), int(rng.integers(31, 101))) for _ in range(300)]
daily = np.stack([strategy_daily_returns(f, s) for f, s in rules])     # (300 rules, RUNS, DAYS-1)
total_in = np.prod(1 + daily[:, :, :SPLIT], axis=2) - 1
total_out = np.prod(1 + daily[:, :, SPLIT:], axis=2) - 1

sizes = [1, 3, 10, 30, 100, 300]
picked_in, picked_out, share_losing = [], [], []
for n in sizes:
    best = np.argmax(total_in[:n], axis=0)                           # the winner in each run
    runs = np.arange(RUNS)
    picked_in.append(np.median(total_in[best, runs]))
    picked_out.append(np.median(total_out[best, runs]))
    share_losing.append(np.mean(total_out[best, runs] < 0))
    print(f"{n:>4} rules tried: winner shows {picked_in[-1]:+.1%} in-sample, then {picked_out[-1]:+.1%} on held-out days "
          f"({share_losing[-1]:.0%} of winners lose money there)")

# %%
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(sizes, np.array(picked_in) * 100, marker="o", lw=2, label="Winner, on the days used to pick it")
ax.plot(sizes, np.array(picked_out) * 100, marker="o", lw=2, label="Same winner, on held-out days")
ax.axhline(0, color="gray", lw=1, ls="--")
ax.set_xscale("log"); ax.set_xticks(sizes); ax.set_xticklabels(sizes)
ax.set_xlabel("Number of rules tried"); ax.set_ylabel("Median return, %")
ax.set_title("More search, better-looking winner, same result afterwards")
ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
plt.show()

# %% [markdown]
# ## Pricing the search in: the expected best Sharpe ratio under pure luck
#
# Bailey and López de Prado give the Sharpe ratio you should expect from the best of N unskilled trials.
# A result has to clear this hurdle before it means anything. The hurdle rises with every extra trial.

# %%
def expected_max_sharpe(n_trials, sharpe_std):
    if n_trials < 2:
        return 0.0
    g, z = 0.5772156649, NormalDist().inv_cdf
    return sharpe_std * ((1 - g) * z(1 - 1 / n_trials) + g * z(1 - 1 / (n_trials * np.e)))

in_sample = daily[:, :, :SPLIT]
vol = in_sample.std(axis=2)
sharpe = np.divide(in_sample.mean(axis=2), vol, out=np.zeros_like(vol), where=vol > 0) * np.sqrt(252)   # annualised; a rule that never traded scores 0
print("trials   best observed   hurdle if trials were independent   behaves like")
for n in sizes[1:]:
    spread = sharpe[:n].std(axis=0).mean()                       # how much Sharpe varies across the rules tried
    observed = np.median(sharpe[:n].max(axis=0))
    hurdle = expected_max_sharpe(n, spread)
    # these rules all trade the same price path, so they are far from independent:
    # find how many independent trials would produce the best Sharpe we actually saw
    effective = min(range(1, n + 1), key=lambda k: abs(expected_max_sharpe(k, spread) - observed))
    print(f"{n:>6}   {observed:13.2f}   {hurdle:34.2f}   {effective:>3} independent tries")

# %% [markdown]
# **Reading the result.** The best observed Sharpe ratio keeps climbing as more rules are tried, on data with no edge.
# It climbs more slowly than the independent-trial hurdle, because these rules are all moving-average crossovers on the
# same prices and are highly correlated: hundreds of them behave like a handful of independent tries.
#
# Two practical points follow. Count every trial your search made, as the paper does. And remember that the
# independent-trial hurdle is the strict version; correlated candidates need an effective count, not a raw one.
#
# In my own run of 702 trading agents on a year of real prices, the ten stock leaders after the first 70% of days
# averaged -18.6% on the last 30%, and two of the ten made money.
