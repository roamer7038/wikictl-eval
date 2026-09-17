#!/usr/bin/env python3
"""Tables of results/main.md, from the scores.

    grade/summary.py results/main-scores-alt.jsonl results/main-scores.jsonl > results/main-tables.md

The first file is the scoring used for the main tables (both readings of
the ambiguous questions accepted), the second the strict one, compared in a
sensitivity table.
"""
import collections
import json
import statistics as st
import sys

MODELS = ["opus", "sonnet", "haiku"]
CONDS = ["B0", "B1", "B2", "B2-best", "B2-lean"]
TASKS = ["L1", "L2", "P2", "P3K", "P3M", "P4", "P5", "P6", "P7", "P8", "P9"]


def load(path):
    by = collections.defaultdict(dict)
    rows = []
    for line in open(path):
        if line.strip():
            r = json.loads(line)
            r["m"] = r["model"].split("-")[1]
            by[(r["m"], r["cond"], r["rep"])][r["task"]] = r
            rows.append(r)
    return by, rows


def ok(r, allow_violations=False):
    return bool(r["quality"].get("success")) and (allow_violations or not r.get("violations"))


def rng(xs, d=2):
    xs = [x for x in xs if x is not None]
    if not xs:
        return "-"
    return f"{st.mean(xs):.{d}f} ({min(xs):.{d}f}–{max(xs):.{d}f})"


def per_rep(by, m, c, allow=False):
    out = []
    for rep in (1, 2, 3):
        d = by.get((m, c, rep))
        if d:
            out.append({"succ": sum(ok(r, allow) for r in d.values()), "usd": sum(r["usd"] for r in d.values()),
                        "min": sum(r["wall_s"] / 60 for r in d.values()),
                        "score": st.mean(r["quality"].get("score") or 0 for r in d.values()), "n": len(d)})
    return out


def overall(by, allow=False):
    print("| モデル | 条件 | 課題 | 成功 | 点 | USD | 分 | 成功 1 回あたり USD |")
    print("|---|---|---|---|---|---|---|---|")
    for m in MODELS:
        for c in CONDS:
            reps = per_rep(by, m, c, allow)
            if not reps:
                continue
            succ = sum(x["succ"] for x in reps)
            usd_per = f"{sum(x['usd'] for x in reps) / succ:.2f}" if succ else "-"
            print(f"| {m} | {c} | {reps[0]['n']} | {rng([x['succ'] for x in reps], 1)} | {rng([x['score'] for x in reps])} | "
                  f"{rng([x['usd'] for x in reps])} | {rng([x['min'] for x in reps], 1)} | {usd_per} |")
    print()


def main():
    by, rows = load(sys.argv[1])
    sby, srows = load(sys.argv[2])
    print("<!-- grade/summary.py の出力 -->\n")
    print("## 全体（両方の読み方を正答）\n")
    print("3 回それぞれで課題を合計した値の平均（最小–最大）。成功 1 回あたり USD は、3 回の USD の合計 ÷ 3 回の成功の合計。\n")
    overall(by)
    print("## 全体（厳密な採点）\n")
    overall(sby)
    print("## 全体（両方の読み方を正答、規則違反を許容）\n")
    overall(by, allow=True)

    print("## B2 系で使われた手段\n")
    print("各 33 グループのうち、1 回以上使ったグループの割合。skill はスキルの読み込み、help は `wikictl help` の実行、"
          "meta・log・show・snapshot は成功した実行（終了コード 0）、search は Bash のコマンドで `wikictl-search` を実行したもの、"
          "no_fetch と many_paths は `--no-fetch` と `xargs` で複数パスを渡したコマンド、violations は規則違反のグループ。\n")
    cols = ["skill", "help", "no_fetch", "many_paths", "meta", "log", "show", "snapshot", "search", "violations"]
    print("| モデル | 条件 | " + " | ".join(cols) + " |")
    print("|---|---|" + "---|" * len(cols))
    for m in MODELS:
        for c in ["B2", "B2-best", "B2-lean"]:
            gs = [r for r in rows if r["m"] == m and r["cond"] == c]
            n = len(gs)
            val = {
                "skill": sum(any(s["skill"]["loaded"] for s in r["sessions"].values()) for r in gs),
                "help": sum(any(s["skill"]["help_calls"] for s in r["sessions"].values()) for r in gs),
                "violations": sum(bool(r.get("violations")) for r in gs),
            }
            for k in ["no_fetch", "many_paths", "meta", "log", "show", "snapshot", "search"]:
                val[k] = sum(bool((r.get("features") or {}).get(k)) for r in gs)
            print(f"| {m} | {c} | " + " | ".join(f"{val[k] / n:.2f}" for k in cols) + " |")
    print()

    print("## 規則違反\n")
    vk = collections.Counter()
    right = 0
    for r in rows:
        if r.get("violations"):
            vk[(r["m"], r["cond"], r["task"], ",".join(sorted(r["violations"])))] += 1
            right += bool(r["quality"].get("success"))
    print("| モデル | 条件 | 課題 | 種類 | グループ |")
    print("|---|---|---|---|---|")
    for (m, c, t, k), n in sorted(vk.items()):
        print(f"| {m} | {c} | {t} | {k} | {n} |")
    print(f"\n違反のあったグループ {sum(vk.values())} のうち、課題に正答していたもの {right}。\n")

    print("## 採点の違いによる P3K と P7 の成功（3 回の合計）\n")
    print("| 課題 | モデル | 条件 | 厳密 | 両方の読み方を正答 |")
    print("|---|---|---|---|---|")
    for t in ["P3K", "P7"]:
        for m in MODELS:
            for c in CONDS[1:]:
                a = sum(ok(r) for r in srows if r["task"] == t and r["m"] == m and r["cond"] == c)
                b = sum(ok(r) for r in rows if r["task"] == t and r["m"] == m and r["cond"] == c)
                if a != b:
                    print(f"| {t} | {m} | {c} | {a}/3 | {b}/3 |")
    print()


if __name__ == "__main__":
    main()
