#!/usr/bin/env python3
"""Best-of-N on prices with no edge at all.

Prices here are random walks, so no strategy can have real skill. We still "discover" strategies
by trying N moving-average rules, keep the best one on the first 70% of days, and then look at
how that winner does on the last 30% it was not chosen on.

Related reading: arXiv:2608.27734 (search-aware evaluation of LLM-discovered trading strategies).
Standard library only. Run: python3 best_of_n.py
"""
import random
import statistics

DAYS, SPLIT, RUNS = 365, 255, 200


def walk(rng):
    price, out = 100.0, []
    for _ in range(DAYS):
        price *= 1 + rng.gauss(0, 0.03)   # 3% daily noise, zero drift
        out.append(price)
    return out


def strategy_returns(prices, fast, slow):
    """Long when the fast average is above the slow one, flat otherwise. Returns (first 70%, last 30%)."""
    growth_in = growth_out = 1.0
    for t in range(slow, DAYS - 1):
        if sum(prices[t - fast + 1:t + 1]) / fast > sum(prices[t - slow + 1:t + 1]) / slow:
            step = prices[t + 1] / prices[t]
            if t < SPLIT:
                growth_in *= step
            else:
                growth_out *= step
    return growth_in - 1, growth_out - 1


def main():
    rng = random.Random(7)
    print("%-10s %-22s %-22s %s" % ("strategies", "winner, first 70%", "same winner, last 30%", "winners that then lost"))
    for n in (1, 10, 50, 300):
        picked_in, picked_out = [], []
        for _ in range(RUNS):
            prices = walk(rng)
            rules = [(rng.randint(2, 30), rng.randint(31, 100)) for _ in range(n)]
            best = max((strategy_returns(prices, f, s) for f, s in rules), key=lambda r: r[0])
            picked_in.append(best[0])
            picked_out.append(best[1])
        lost = sum(r < 0 for r in picked_out) / RUNS
        print("%-10d %-22s %-22s %.0f%%" % (n, "%+.1f%% (median)" % (100 * statistics.median(picked_in)),
                                           "%+.1f%% (median)" % (100 * statistics.median(picked_out)), 100 * lost))
    print("\nThe more rules you try, the better the winner looks, and none of it carries over.")


if __name__ == "__main__":
    main()
