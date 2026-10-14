#!/usr/bin/env python3
"""The same strategies, ranked under different trading costs.

Three made-up traders act on one synthetic minute-by-minute price path with a small upward drift:
a scalper that trades constantly, a swing trader that trades sometimes, and a holder that buys once.
Nothing changes between rows except the cost charged per trade.

Related reading: arXiv:2610.05077 (execution assumptions change short-horizon Sharpe rankings).
Standard library only. Run: python3 cost_flip.py
"""
import random

MINUTES = 540   # nine hours


def path(rng):
    price, out = 100.0, []
    for _ in range(MINUTES):
        price *= 1 + rng.gauss(0.00002, 0.0009)
        out.append(price)
    return out


def run(prices, lookback, cost):
    """Long when price is above its `lookback`-minute average. Returns (return, number of trades)."""
    cash, units, trades = 1.0, 0.0, 0
    for t in range(lookback, MINUTES):
        above = prices[t] > sum(prices[t - lookback:t]) / lookback
        if above and not units:
            units, cash, trades = cash * (1 - cost) / prices[t], 0.0, trades + 1
        elif not above and units:
            cash, units, trades = units * prices[t] * (1 - cost), 0.0, trades + 1
    return cash + units * prices[-1] - 1, trades


def main():
    rng = random.Random(3)
    paths = [path(rng) for _ in range(300)]
    traders = {"scalper (3-min average)": 3, "swing (60-min average)": 60}
    print("%-22s %-26s %-26s %s" % ("cost per trade", "scalper", "swing", "buy and hold"))
    for cost in (0.0, 0.0005, 0.002):
        row = []
        for name, lookback in traders.items():
            results = [run(p, lookback, cost) for p in paths]
            row.append("%+.2f%% (%d trades)" % (100 * sum(r for r, _ in results) / len(results), sum(n for _, n in results) / len(results)))
        hold = sum(p[-1] / p[0] * (1 - cost) - 1 for p in paths) / len(paths)
        print("%-22s %-26s %-26s %+.2f%%" % ("%.2f%%" % (100 * cost), row[0], row[1], 100 * hold))
    print("\nAt zero cost the busiest trader can look fine. Charge a realistic fee and the order reverses.")


if __name__ == "__main__":
    main()
