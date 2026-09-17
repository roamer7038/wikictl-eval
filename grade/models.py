#!/usr/bin/env python3
"""Cost per success of each model, and when a stronger model is cheaper.

    grade/models.py results/main-scores.jsonl [results/main-scores-alt.jsonl] > results/model-cost.md

For every task, condition and model: the success rate p over the
repetitions, the mean USD of an attempt c, and the expected USD per success
c / p, which is what repeating an attempt until it succeeds costs on
average. Conditions B1, B2, B2-best and B2-lean are also pooled (12 attempts
per task and model) for steadier estimates. A stronger model s is cheaper
per success than a weaker model w exactly when p_w < p_s * c_w / c_s: the
weaker model must succeed at least c_w / c_s times as often as the stronger
one to be worth using.
"""
import collections
import json
import math
import statistics as st
import sys

MODELS = ["opus", "sonnet", "haiku"]
TASKS = ["L1", "L2", "P2", "P3K", "P3M", "P4", "P5", "P6", "P7", "P8", "P9"]
POOL = ["B1", "B2", "B2-best", "B2-lean"]
KIND = {"L1": "値", "L2": "値", "P2": "全文検索", "P3K": "集計", "P3M": "集計", "P4": "履歴", "P5": "曖昧な表現",
        "P6": "多段の参照", "P7": "照合", "P8": "続き", "P9": "同時の書き込み"}


def load(path):
    cells = collections.defaultdict(list)
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        m = r["model"].split("-")[1]
        tok_in = sum((s["tokens"]["input"] or 0) + (s["tokens"]["cache_read"] or 0) + (s["tokens"]["cache_write"] or 0)
                     for s in r["sessions"].values())
        cells[(r["task"], r["cond"], m)].append({
            "usd": r["usd"], "ok": bool(r["quality"].get("success")) and not r.get("violations"),
            "score": r["quality"].get("score") or 0.0, "in": tok_in,
            "out": sum((s["tokens"]["output"] or 0) for s in r["sessions"].values()),
            "turns": sum((s.get("turns") or 0) for s in r["sessions"].values()),
            "min": r["wall_s"] / 60})
    return cells


def summary(attempts):
    n = len(attempts)
    if not n:
        return None
    s = sum(a["ok"] for a in attempts)
    c = st.mean(a["usd"] for a in attempts)
    return {"n": n, "succ": s, "p": s / n, "c": c, "ecs": c / (s / n) if s else math.inf,
            "score": st.mean(a["score"] for a in attempts), "in": st.mean(a["in"] for a in attempts),
            "out": st.mean(a["out"] for a in attempts), "turns": st.mean(a["turns"] for a in attempts),
            "min": st.mean(a["min"] for a in attempts)}


def usd(x, d=3):
    return "∞" if x == math.inf else f"{x:.{d}f}"


def cheapest(sums):
    best = min(sums, key=lambda m: sums[m]["ecs"])
    return best if sums[best]["ecs"] != math.inf else "-"


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def overall_rows(cells, title):
    print(f"| {title} | 試行 | 成功率 | 1 回の平均 USD | 成功 1 回あたり USD |")
    print("|---|---|---|---|---|")
    for m in MODELS:
        s = summary([a for t in TASKS for c in POOL for a in cells.get((t, c, m), [])])
        print(f"| {m} | {s['n']} | {s['p']:.2f} | {s['c']:.3f} | {usd(s['ecs'])} |")
    print()


def main():
    strict = load(sys.argv[1])
    alt = load(sys.argv[2]) if len(sys.argv) > 2 else None
    # Sections 1-5 use the scores that accept both readings of P3K when they
    # are given, since how a question was worded is not what separates the
    # models; section 6 compares the two.
    cells = alt or strict
    pooled = {(t, m): summary([a for c in POOL for a in cells.get((t, c, m), [])]) for t in TASKS for m in MODELS}

    print("# モデルごとの成功 1 回あたりの費用と、上位のモデルが安くなる条件\n")
    print("[main.md](main.md) の本番（423 グループ）から [`grade/models.py`](../grade/models.py) で集計した。"
          "USD は公開の単価での換算。" + ("1〜5 節は、P3K の問題文の 2 通りの読み方をどちらも正答とした採点による（6 節を参照）。" if alt else "") + "\n")
    print("## 用語\n")
    print("- p: 成功率（全問正答、規則違反なし）。c: 1 回の試行の平均 USD。")
    print("- 成功 1 回あたりの期待 USD = c / p。成功するまで試行を繰り返すときの平均の費用。p = 0 は ∞。")
    print("- 上位のモデル s が下位のモデル w より成功 1 回あたり安くなるのは、p_w / p_s < c_w / c_s のとき。"
          "つまり、下位のモデルの費用が上位の何割かを表す c_w / c_s が、下位のモデルが使える成功率の比の上限になる。\n")

    print("## 1. 全体\n")
    print("B1・B2・B2-best・B2-lean の 4 条件 × 11 課題 × 3 回を合わせた値。\n")
    print("| モデル | 試行 | 成功率 | 1 回の平均 USD | 成功 1 回あたり USD | 入力トークン（1 回平均） | 出力トークン（1 回平均） | ターン（1 回平均） |")
    print("|---|---|---|---|---|---|---|---|")
    for m in MODELS:
        s = summary([a for t in TASKS for c in POOL for a in cells.get((t, c, m), [])])
        print(f"| {m} | {s['n']} | {s['p']:.2f} | {s['c']:.3f} | {usd(s['ecs'])} | {s['in'] / 1e3:.0f}k | {s['out'] / 1e3:.1f}k | {s['turns']:.1f} |")
    print()
    base = {m: summary([a for t in TASKS for c in POOL for a in cells.get((t, c, m), [])]) for m in MODELS}
    print(f"1 回の費用の比: Sonnet / Opus = {base['sonnet']['c'] / base['opus']['c']:.2f}、"
          f"Haiku / Opus = {base['haiku']['c'] / base['opus']['c']:.2f}、Haiku / Sonnet = {base['haiku']['c'] / base['sonnet']['c']:.2f}。"
          f"入力トークンの比: Sonnet / Opus = {base['sonnet']['in'] / base['opus']['in']:.2f}、"
          f"Haiku / Opus = {base['haiku']['in'] / base['opus']['in']:.2f}。"
          "単価の比は Sonnet / Opus = 0.40、Haiku / Opus = 0.20。\n")

    print("## 2. 課題ごと（4 条件を合わせた 12 回）\n")
    print("課題は、3 モデルを合わせた成功率の高い順（易しい順）に並べた。\n")
    order = sorted(TASKS, key=lambda t: -st.mean(pooled[(t, m)]["p"] for m in MODELS))
    print("| 課題 | 型 | 全体の成功率 | 成功率（O / S / H） | 1 回の USD（O / S / H） | 成功 1 回あたり USD（O / S / H） | 最安 | 入力トークン（O / S / H） |")
    print("|---|---|---|---|---|---|---|---|")
    rows = []
    for t in order:
        ps = {m: pooled[(t, m)] for m in MODELS}
        allp = st.mean(ps[m]["p"] for m in MODELS)
        rows.append((t, allp, ps))
        print(f"| {t} | {KIND[t]} | {allp:.2f} | " + " / ".join(f"{ps[m]['p']:.2f}" for m in MODELS) + " | "
              + " / ".join(f"{ps[m]['c']:.2f}" for m in MODELS) + " | " + " / ".join(usd(ps[m]['ecs'], 2) for m in MODELS)
              + f" | {cheapest(ps)} | " + " / ".join(f"{ps[m]['in'] / 1e3:.0f}k" for m in MODELS) + " |")
    print()

    print("## 3. 損益分岐（4 条件を合わせた 12 回）\n")
    print("各ペアで、下位のモデルが上位より安く済むために必要な成功率の比の上限（c_w / c_s）と、観測した比（p_w / p_s）。"
          "観測した比が上限を下回ると上位のモデルのほうが成功 1 回あたり安い（「上位」）。\n")
    print("| 課題 | Sonnet 対 Opus: 上限 / 観測 | 判定 | Haiku 対 Opus: 上限 / 観測 | 判定 | Haiku 対 Sonnet: 上限 / 観測 | 判定 |")
    print("|---|---|---|---|---|---|---|")
    flips = collections.Counter()
    for t, _, ps in rows:
        parts = []
        for w, s in (("sonnet", "opus"), ("haiku", "opus"), ("haiku", "sonnet")):
            limit = ps[w]["c"] / ps[s]["c"]
            obs = ps[w]["p"] / ps[s]["p"] if ps[s]["p"] else math.inf
            if ps[s]["p"] == 0 and ps[w]["p"] == 0:
                verdict = "両方 0"
            elif obs < limit:
                verdict = "上位"
                flips[(w, s)] += 1
            else:
                verdict = "下位"
            parts.append(f"{limit:.2f} / {'∞' if obs == math.inf else f'{obs:.2f}'} | {verdict}")
        print(f"| {t} | " + " | ".join(parts) + " |")
    print()
    print("上位のモデルのほうが成功 1 回あたり安かった課題の数（11 課題中）: "
          f"Opus < Sonnet {flips[('sonnet', 'opus')]}、Opus < Haiku {flips[('haiku', 'opus')]}、"
          f"Sonnet < Haiku {flips[('haiku', 'sonnet')]}。\n")

    print("## 4. 難しさとの関係\n")
    allps = [r[1] for r in rows]
    ratio_hi = [r[2]["haiku"]["in"] / r[2]["opus"]["in"] for r in rows]
    ratio_si = [r[2]["sonnet"]["in"] / r[2]["opus"]["in"] for r in rows]
    ratio_hc = [r[2]["haiku"]["c"] / r[2]["opus"]["c"] for r in rows]
    def ecs_ratio(r, w, s):
        a, b = r[2][w]["ecs"], r[2][s]["ecs"]
        return math.inf if a == math.inf else (a / b if b not in (0, math.inf) else 0.0)
    ecs_ho = [ecs_ratio(r, "haiku", "opus") for r in rows]
    print("11 課題について、全体の成功率（高いほど易しい）との順位相関（Spearman）:\n")
    print(f"- 入力トークンの比 Haiku / Opus: {spearman(allps, ratio_hi):+.2f}")
    print(f"- 入力トークンの比 Sonnet / Opus: {spearman(allps, ratio_si):+.2f}")
    print(f"- 1 回の費用の比 Haiku / Opus: {spearman(allps, ratio_hc):+.2f}")
    finite = [(a, e) for a, e in zip(allps, ecs_ho)]
    print(f"- 成功 1 回あたりの費用の比 Haiku / Opus（Haiku の成功率 0 は最大の順位）: {spearman([a for a, _ in finite], [e if e != math.inf else 1e9 for _, e in finite]):+.2f}\n")
    print("| 課題 | 全体の成功率 | Haiku の成功率 | 入力トークンの比 H/O | 1 回の費用の比 H/O | 成功 1 回あたりの比 H/O | 成功 1 回あたりの比 S/O |")
    print("|---|---|---|---|---|---|---|")
    for r, a, b, c, e in zip(rows, allps, ratio_hi, ratio_hc, ecs_ho):
        so = ecs_ratio(r, "sonnet", "opus")
        print(f"| {r[0]} | {a:.2f} | {r[2]['haiku']['p']:.2f} | {b:.2f} | {c:.2f} | {usd(e, 2)} | {usd(so, 2)} |")
    print()

    qdc(pooled)
    print("## 6. 条件ごと（3 回）\n")
    print("成功 1 回あたり USD（O / S / H）と最安のモデル。3 回だけなので、成功率は 0、0.33、0.67、1 のいずれか。\n")
    conds = ["B0"] + POOL
    print("| 課題 | " + " | ".join(conds) + " |")
    print("|---|" + "---|" * len(conds))
    for t in order:
        parts = []
        for c in conds:
            ss = {m: summary(cells.get((t, c, m), [])) for m in MODELS}
            if any(v is None for v in ss.values()):
                parts.append("-")
                continue
            parts.append(" / ".join(usd(ss[m]["ecs"], 2) for m in MODELS) + f" → {cheapest(ss)}")
        print(f"| {t} | " + " | ".join(parts) + " |")
    print()
    if alt:
        sensitivity(strict, alt)


def qdc(pooled):
    """Quality, delivery and cost per task, and which models are not beaten
    on all three at once."""
    print("## 5. 品質・時間・費用（4 条件を合わせた 12 回）\n")
    print("成功 1 回あたりの分 = 1 回の平均の実時間 ÷ 成功率。パレートは、成功率・成功 1 回あたりの分・"
          "成功 1 回あたりの USD の 3 つすべてで他のモデルに劣ってはいないモデル。\n")
    print("| 課題 | 成功率（O / S / H） | 成功 1 回あたりの分（O / S / H） | 成功 1 回あたり USD（O / S / H） | Q 最高 | D 最速 | C 最安 | パレート |")
    print("|---|---|---|---|---|---|---|---|")
    order = sorted(TASKS, key=lambda t: -st.mean(pooled[(t, m)]["p"] for m in MODELS))
    tally = collections.Counter()
    for t in order:
        d = {m: pooled[(t, m)] for m in MODELS}
        ets = {m: (d[m]["min"] / d[m]["p"] if d[m]["p"] else math.inf) for m in MODELS}
        bestq = max(d[m]["p"] for m in MODELS)
        q = [m for m in MODELS if d[m]["p"] == bestq]
        dbest = [m for m in MODELS if ets[m] == min(ets.values())]
        cbest = [m for m in MODELS if d[m]["ecs"] == min(d[x]["ecs"] for x in MODELS)]
        pareto = [m for m in MODELS if not any(
            x != m and d[x]["p"] >= d[m]["p"] and ets[x] <= ets[m] and d[x]["ecs"] <= d[m]["ecs"]
            and (d[x]["p"] > d[m]["p"] or ets[x] < ets[m] or d[x]["ecs"] < d[m]["ecs"]) for x in MODELS)]
        for m in pareto:
            tally[m] += 1
        f = lambda key, dd=2: " / ".join(usd(key[m], dd) for m in MODELS)  # noqa: E731
        print(f"| {t} | " + " / ".join(f"{d[m]['p']:.2f}" for m in MODELS) + " | " + f(ets, 1) + " | "
              + " / ".join(usd(d[m]["ecs"], 2) for m in MODELS) + f" | {'・'.join(q)} | {'・'.join(dbest)} | "
              + f"{'・'.join(cbest)} | {'・'.join(pareto)} |")
    print()
    print("パレートに残った課題の数（11 課題中）: " + "、".join(f"{m} {tally[m]}" for m in MODELS) + "。\n")


def sensitivity(cells, alt):
    print("## 7. 問題文の解釈による違い（P3K・P7）\n")
    print("2 つの問いが 2 通りに読める。P3K の「v1.37 で beta の段階に入った」は、その版から始まる段をすべて数える"
          "（正解）か、前の段が同じ段階のもの（既定値が変わっただけのもの）を除くか。Opus は 12 回中 11 回で後者の"
          "読み方をとり、F1 0.94〜0.97 で成功の閾値 0.95 を下回った。P7 の 2 問目の「ページに stable の段階がないもの」は、"
          "ページ自体がない gate を含むかどうかで、Sonnet の失敗 4 回はこれによる。"
          "どちらの読み方も正答とした採点（`grade/score.py --accept-alternatives`）での値を並べる。\n")
    overall_rows(cells, "正解のみ")
    overall_rows(alt, "両方の読み方を正答")
    print("| 課題 | 読み方 | 成功率（O / S / H） | 成功 1 回あたり USD（O / S / H） | 最安 |")
    print("|---|---|---|---|---|")
    for t in ("P3K", "P7"):
      for name, cs in (("正解のみ", cells), ("両方を正答", alt)):
        ps = {m: summary([a for c in POOL for a in cs.get((t, c, m), [])]) for m in MODELS}
        print(f"| {t} | {name} | " + " / ".join(f"{ps[m]['p']:.2f}" for m in MODELS) + " | "
              + " / ".join(usd(ps[m]['ecs'], 2) for m in MODELS) + f" | {cheapest(ps)} |")
    print()


if __name__ == "__main__":
    main()
