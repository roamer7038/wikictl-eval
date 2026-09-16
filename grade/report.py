#!/usr/bin/env python3
"""Summarise graded groups as Markdown tables.

    grade/grade.py runs/*-pilot > results/raw/pilot.jsonl
    grade/report.py results/raw/pilot.jsonl > results/pilot.md

Each row is one task, condition and model; values are the mean over
repetitions, with the minimum and maximum when there are several.
"""
import json
import statistics
import sys
from collections import defaultdict

MODEL_ORDER = ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"]


def fmt(vals, digits=2):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "-"
    m = statistics.mean(vals)
    if len(vals) == 1 or min(vals) == max(vals):
        return f"{m:.{digits}f}"
    return f"{m:.{digits}f} ({min(vals):.{digits}f}–{max(vals):.{digits}f})"


def sessions_sum(g, key, names=None):
    total = 0
    for n, s in g["sessions"].items():
        if names and n not in names:
            continue
        v = key(s)
        if v is None:
            return None
        total += v
    return total


def wiki_calls(s):
    return sum(b["calls"] for p, b in s["commands"]["by_program"].items() if p in ("wikictl", "git", "rg"))


def speed_cost(g, names=None):
    return {
        "usd": sessions_sum(g, lambda s: s["usage"].get("usd"), names),
        "min": sessions_sum(g, lambda s: s["wall_ms"] / 60000, names),
        "turns": sessions_sum(g, lambda s: s["usage"].get("num_turns"), names),
        "cmds": sessions_sum(g, wiki_calls, names),
        "tools": sessions_sum(g, lambda s: sum(s["tools"].values()), names),
        "out_kb": sessions_sum(g, lambda s: sum(b["stdout_bytes"] for b in s["commands"]["by_program"].values()) / 1024, names),
    }


def key(g):
    return (g["task"], g["cond"], MODEL_ORDER.index(g["model"]) if g["model"] in MODEL_ORDER else 9)


def table(rows, cols):
    out = ["| " + " | ".join(c for c, _ in cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(f(r) for _, f in cols) + " |")
    return "\n".join(out)


def main():
    groups = [json.loads(l) for f in sys.argv[1:] for l in open(f) if l.strip()]
    by = defaultdict(list)
    for g in groups:
        by[(g["task"], g["cond"], g["model"])].append(g)
    keys = sorted(by, key=lambda k: key({"task": k[0], "cond": k[1], "model": k[2]}))

    def rows(task):
        return [(k, by[k]) for k in keys if k[0] == task]

    def base_cols(names=None):
        return [
            ("cond", lambda r: r[0][1]), ("model", lambda r: r[0][2]), ("n", lambda r: str(len(r[1]))),
            ("USD", lambda r: fmt([speed_cost(g, names)["usd"] for g in r[1]], 3)),
            ("min", lambda r: fmt([speed_cost(g, names)["min"] for g in r[1]], 1)),
            ("turns", lambda r: fmt([speed_cost(g, names)["turns"] for g in r[1]], 0)),
            ("tool calls", lambda r: fmt([speed_cost(g, names)["tools"] for g in r[1]], 0)),
            ("wikictl/git/rg calls", lambda r: fmt([speed_cost(g, names)["cmds"] for g in r[1]], 0)),
            ("cmd stdout KiB", lambda r: fmt([speed_cost(g, names)["out_kb"] for g in r[1]], 0)),
        ]

    print("# Results\n")
    for task, title in (("T1", "T1 recall values (72 pages)"), ("T4", "T4 recall values (1,012 pages)")):
        if not rows(task):
            continue
        print(f"## {title}\n")
        print(table(rows(task), base_cols()[:3] + [
            ("correct /10", lambda r: fmt([g["quality"]["correct"] for g in r[1]], 1)),
            ("stale", lambda r: fmt([g["quality"]["stale"] for g in r[1]], 1)),
            ("unknown", lambda r: fmt([g["quality"]["unknown"] for g in r[1]], 1)),
            ("wrong", lambda r: fmt([g["quality"]["wrong"] for g in r[1]], 1)),
        ] + base_cols()[3:]))
        print()
    if rows("T2"):
        print("## T2 continue in another session\n")
        print("Session 2 (all 24 services) and the wiki written by both sessions.\n")
        print(table(rows("T2"), base_cols(["s2"])[:3] + [
            ("s1 fields /36", lambda r: fmt([g["quality"]["s1"]["correct"] for g in r[1]], 1)),
            ("s2 fields /72", lambda r: fmt([g["quality"]["s2"]["correct"] for g in r[1]], 1)),
            ("wiki commits", lambda r: fmt([g["wiki"]["commits"] for g in r[1]], 0)),
            ("wiki files", lambda r: fmt([len(g["wiki"]["files"]) for g in r[1]], 0)),
            ("lint", lambda r: fmt([len(g["wiki"]["lint"]) for g in r[1]], 0)),
        ] + [(f"s2 {c}", f) for c, f in base_cols(["s2"])[3:]] + [
            ("s1 USD", lambda r: fmt([speed_cost(g, ["s1"])["usd"] for g in r[1]], 3)),
        ]))
        print()
    if rows("T3"):
        print("## T3 three agents write at the same time\n")
        print("Sums over the three agents; 15 incidents expected.\n")
        print(table(rows("T3"), base_cols()[:3] + [
            ("pages missing", lambda r: fmt([g["quality"]["pages_missing"] for g in r[1]], 1)),
            ("rows missing", lambda r: fmt([g["quality"]["rows_missing"] for g in r[1]], 1)),
            ("rows duplicated", lambda r: fmt([g["quality"]["rows_duplicated"] for g in r[1]], 1)),
            ("seeded lost", lambda r: fmt([g["quality"]["seeded_lost"] for g in r[1]], 1)),
            ("sorted", lambda r: fmt([float(g["quality"]["index_sorted"]) for g in r[1]], 2)),
            ("lint", lambda r: fmt([len(g["wiki"]["lint"]) for g in r[1]], 0)),
        ] + base_cols()[3:]))
        print()
    bad = [(g["group"], n, s["exit"], s["timed_out"], s["usage"].get("result_subtype"))
           for g in groups for n, s in g["sessions"].items()
           if s["exit"] != 0 or s["timed_out"] or not s["usage"].get("complete") or s["usage"].get("is_error")]
    if bad:
        print("## Sessions that did not finish normally\n")
        print("| group | session | exit | timed out | result |\n|---|---|---|---|---|")
        for b in bad:
            print("| " + " | ".join(map(str, b)) + " |")


if __name__ == "__main__":
    main()
