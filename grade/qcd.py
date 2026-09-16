#!/usr/bin/env python3
"""Summarise scores (grade/score.py) as quality, cost and delivery tables.

    grade/score.py <groups>... > scores.jsonl
    grade/qcd.py scores.jsonl [--baseline B1] > qcd.md

Q is the score of a task (mean over questions of 1/0 or F1) and its success
(every question correct, without breaking the rules of the prompt, such as
reading the wikictl mirror with git under B2); C is USD; D is wall time in minutes (for P9, the
longest of the three agents). Values are means over repetitions; n is the
number of repetitions.
"""
import argparse
import json
import statistics
from collections import defaultdict

MODELS = ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"]
SHORT = {"claude-opus-5": "opus", "claude-sonnet-5": "sonnet", "claude-haiku-4-5": "haiku"}
TASKS = ["L1", "L2", "P2", "P3K", "P3M", "P4", "P5", "P6", "P7", "P8", "P9"]
COND_ORDER = ["B0", "B1", "B2", "B2-trigger", "B2-help", "B2-nofetch", "B2-skill", "B2-proto", "B2-best", "B2-lean"]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def f(x, d=2):
    return "-" if x is None else f"{x:.{d}f}"


def load(paths):
    rows = [json.loads(l) for p in paths for l in open(p) if l.strip()]
    by = defaultdict(list)
    for r in rows:
        if r.get("rate_limited"):
            continue
        by[(r["task"], r["cond"], r["model"], r.get("delay_ms"))].append(r)
    return by


def cell(groups):
    return {
        "n": len(groups),
        "score": mean([g["quality"].get("score") for g in groups]),
        # A group that broke the rules of the prompt does not count as a success.
        "success": mean([float(bool(g["quality"].get("success")) and not g.get("violations")) for g in groups]),
        "usd": mean([g["usd"] for g in groups]),
        "min": mean([g["wall_s"] / 60 for g in groups]),
        "calls": mean([g["tool_calls"] for g in groups]),
        "timeouts": sum(any(s["timed_out"] for s in g["sessions"].values()) for g in groups),
        "violations": sum(bool(g.get("violations")) for g in groups),
    }


def top_programs(groups, k=3):
    agg = defaultdict(lambda: [0, 0.0])
    for g in groups:
        for name, e in (g.get("executions") or {}).items():
            agg[name][0] += e["runs"]
            agg[name][1] += e["s"]
    n = max(len(groups), 1)
    items = sorted(agg.items(), key=lambda kv: -kv[1][1])[:k]
    return ", ".join(f"{name} {runs / n:.0f}×/{s / n:.0f}s" for name, (runs, s) in items) or "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scores", nargs="+")
    ap.add_argument("--baseline", default="B1")
    a = ap.parse_args()
    by = load(a.scores)
    delays = sorted({k[3] for k in by})
    conds = [c for c in COND_ORDER if any(k[1] == c for k in by)]
    print("# QCD\n")
    print("Q: score 0–1 (success rate), C: USD, D: minutes. Mean over n repetitions.\n")
    for delay in delays:
        print(f"## Delay {delay} ms\n")
        print("### Overall (tasks each condition ran)\n")
        print("| model | cond | tasks | mean score | success rate | total USD | total min | USD per success |")
        print("|---|---|---|---|---|---|---|---|")
        for m in MODELS:
            for c in conds:
                cells = [cell(by[(t, c, m, delay)]) for t in TASKS if by.get((t, c, m, delay))]
                if not cells:
                    continue
                succ = sum(x["success"] for x in cells)
                usd = sum(x["usd"] for x in cells)
                print(f"| {SHORT[m]} | {c} | {len(cells)} | {f(mean([x['score'] for x in cells]))} | "
                      f"{f(succ / len(cells))} | {f(usd)} | {f(sum(x['min'] for x in cells), 1)} | "
                      f"{f(usd / succ) if succ else '-'} |")
        print()
        for t in TASKS:
            keys = [(t, c, m, delay) for m in MODELS for c in conds if by.get((t, c, m, delay))]
            if not keys:
                continue
            print(f"### {t}\n")
            print("| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |")
            print("|---|---|---|---|---|---|---|---|---|---|---|")
            for k in keys:
                x = cell(by[k])
                print(f"| {SHORT[k[2]]} | {k[1]} | {x['n']} | {f(x['score'])} | {f(x['success'])} | {f(x['usd'], 3)} | "
                      f"{f(x['min'], 1)} | {f(x['calls'], 0)} | {x['timeouts']} | {x['violations']} | {top_programs(by[k])} |")
            print()
        print(f"### Difference from {a.baseline} (score, USD ratio, time ratio)\n")
        others = [c for c in conds if c not in ("B0", a.baseline)]
        print("| model | task | " + " | ".join(others) + " |")
        print("|---|---|" + "---|" * len(others))
        for m in MODELS:
            for t in TASKS:
                base = by.get((t, a.baseline, m, delay))
                if not base:
                    continue
                b = cell(base)
                parts = []
                for c in others:
                    g = by.get((t, c, m, delay))
                    if not g:
                        parts.append("-")
                        continue
                    x = cell(g)
                    ds = x["score"] - b["score"] if x["score"] is not None and b["score"] is not None else None
                    ru = x["usd"] / b["usd"] if b["usd"] else None
                    rt = x["min"] / b["min"] if b["min"] else None
                    parts.append(f"{'+' if ds and ds > 0 else ''}{f(ds)} / ×{f(ru)} / ×{f(rt)}")
                print(f"| {SHORT[m]} | {t} | " + " | ".join(parts) + " |")
        print()


if __name__ == "__main__":
    main()
