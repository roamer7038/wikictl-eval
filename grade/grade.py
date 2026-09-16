#!/usr/bin/env python3
"""Grade and measure groups of runs.

    grade/grade.py runs/<group>...   > results/raw/<name>.jsonl

prints one JSON object per group: quality from the answers and the final
wiki, and cost and speed per session from stream.jsonl and cmdlog.tsv.
"""
import csv
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES = json.load(open(os.path.join(ROOT, "grade", "prices.json")))


# ---- cost and speed --------------------------------------------------------

def usage(stream):
    """Tokens and USD of a session from the result event of stream-json.

    The assistant events of stream-json under-report output tokens, so the
    totals come from modelUsage of the result event, per model. Cache writes
    are split into 5-minute and 1-hour writes in the proportion of the
    result's usage.cache_creation. api_calls counts the distinct message ids
    of the assistant events. A session killed before its result event has
    no totals ("complete": false).
    """
    ids, result = set(), None
    for line in open(stream):
        try:
            j = json.loads(line)
        except ValueError:
            continue
        if j.get("type") == "result":
            result = j
        elif j.get("type") == "assistant" and isinstance(j.get("message"), dict):
            ids.add(j["message"].get("id"))
    out = {"api_calls": len(ids), "complete": result is not None}
    if result is None:
        return out
    cc = (result.get("usage") or {}).get("cache_creation") or {}
    w5, w1 = cc.get("ephemeral_5m_input_tokens", 0), cc.get("ephemeral_1h_input_tokens", 0)
    share_1h = w1 / (w5 + w1) if w5 + w1 else 0.0
    models, usd = {}, 0.0
    for name, m in (result.get("modelUsage") or {}).items():
        p = PRICES.get(m.get("canonicalModel") or name) or PRICES.get(name)
        t = {"input": m.get("inputTokens", 0), "output": m.get("outputTokens", 0),
             "cache_read": m.get("cacheReadInputTokens", 0), "cache_write": m.get("cacheCreationInputTokens", 0)}
        t["usd"] = None if p is None else round((
            t["input"] * p["input"] + t["output"] * p["output"] + t["cache_read"] * p["input"] * 0.1
            + t["cache_write"] * p["input"] * (1.25 * (1 - share_1h) + 2 * share_1h)) / 1e6, 5)
        usd = None if usd is None or t["usd"] is None else usd + t["usd"]
        models[name] = t
    for k in ("input", "output", "cache_read", "cache_write"):
        out[k] = sum(t[k] for t in models.values())
    out.update({"models": models, "usd": None if usd is None else round(usd, 5),
                "reported_usd": result.get("total_cost_usd"), "duration_ms": result.get("duration_ms"),
                "num_turns": result.get("num_turns"), "is_error": result.get("is_error"),
                "result_subtype": result.get("subtype")})
    return out


def by_agent(row):
    """Whether the agent ran the command, rather than Claude Code itself,
    which runs git for its git status with the caller "claude"."""
    callers = row.get("callers")
    if callers is not None:
        return callers.split(",")[0] != "claude"
    return not row["argv"].startswith(("git -c core.hooksPath=/dev/null", "git -c core.askPass=",
                                       "git -c core.fsmonitor="))


def commands(cmdlog):
    rows = [r for r in csv.DictReader(open(cmdlog), delimiter="\t", quoting=csv.QUOTE_NONE) if by_agent(r)]
    out = {"calls": len(rows), "by_program": {}}
    for r in rows:
        prog = r["argv"].split(" ", 1)[0]
        b = out["by_program"].setdefault(prog, {"calls": 0, "ms": 0, "stdout_bytes": 0, "failed": 0})
        b["calls"] += 1
        b["ms"] += int(r["ms"])
        b["stdout_bytes"] += int(r["stdout_bytes"])
        b["failed"] += r["exit"] != "0"
    return out


def tool_calls(stream):
    n = {}
    for line in open(stream):
        try:
            j = json.loads(line)
        except ValueError:
            continue
        if j.get("type") != "assistant":
            continue
        for c in (j.get("message") or {}).get("content") or []:
            if c.get("type") == "tool_use":
                n[c["name"]] = n.get(c["name"], 0) + 1
    return n


# ---- wiki ------------------------------------------------------------------

def git(remote, *args):
    return subprocess.run(["git", "-C", remote, *args], capture_output=True, text=True, check=True).stdout


def lint(group, remote, paths):
    """wikictl lint of the given pages, run on the final wiki."""
    pages = [p for p in paths if p.endswith(".md") and "/" in p]
    if not pages:
        return []
    cache = os.path.join(group, ".grade-cache")
    cfg = os.path.join(group, ".grade-config.yaml")
    with open(cfg, "w") as f:
        f.write(f"repo: {remote}\nauthor:\n  name: grader\n  email: grader@example.invalid\n")
    r = subprocess.run([os.path.join(ROOT, "build", "bin", "wikictl"), "--config", cfg, "--json", "lint", *pages],
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HOME": group, "XDG_CACHE_HOME": cache})
    try:
        return json.loads(r.stdout).get("items", [])
    except ValueError:
        return [{"code": "lint_failed", "message": r.stderr.strip()}]


def wiki_changes(group, meta):
    remote = os.path.join(group, "remote.git")
    base, final = meta["base_commit"], meta["final_commit"]
    if base == final:
        return {"commits": 0, "files": [], "lint": []}
    files = [l.split("\t") for l in git(remote, "diff", "--name-status", "--no-renames", base, final).splitlines()]
    present = set(git(remote, "ls-tree", "-r", "--name-only", final).splitlines())
    items = lint(group, remote, [f for _, f in files if f in present])
    return {"commits": int(git(remote, "rev-list", "--count", f"{base}..{final}")),
            "files": [{"status": s, "path": f} for s, f in files],
            "lint": [{k: i.get(k) for k in ("path", "code")} for i in items]}


# ---- quality ---------------------------------------------------------------

def norm(v):
    if v is None:
        return None
    s = str(v).strip().strip("`").strip()
    return re.sub(r"\s+", " ", s).casefold()


def load_answers(path):
    try:
        return json.load(open(path)), None
    except FileNotFoundError:
        return {}, "missing"
    except ValueError as e:
        return {}, f"invalid: {e}"


def grade_values(answers_path, qs):
    ans, err = load_answers(answers_path)
    out = {"answers_error": err, "items": {}}
    for k, q in qs.items():
        a = ans.get(k) if isinstance(ans, dict) else None
        if norm(a) in {norm(x) for x in [q["answer"], *q.get("accept", [])]}:
            v = "correct"
        elif a is None or norm(a) in ("", "null"):
            v = "unknown"
        elif q["stale"] is not None and norm(a) in {norm(x) for x in [q["stale"], *q.get("accept_stale", [])]}:
            v = "stale"
        else:
            v = "wrong"
        out["items"][k] = {"verdict": v, "answer": a}
    vs = [i["verdict"] for i in out["items"].values()]
    out.update({c: vs.count(c) for c in ("correct", "stale", "unknown", "wrong")})
    out["total"] = len(vs)
    return out


def grade_deploy(answers_path, services, truth):
    ans, err = load_answers(answers_path)
    ok = fields = 0
    wrong = []
    for s in services:
        a = ans.get(s) if isinstance(ans, dict) else None
        for k in ("replicas", "memory", "port"):
            fields += 1
            got = a.get(k) if isinstance(a, dict) else None
            if norm(got) == norm(truth[s][k]):
                ok += 1
            else:
                wrong.append([s, k, got, truth[s][k]])
    return {"answers_error": err, "fields": fields, "correct": ok, "services_all_correct":
            sum(all(w[0] != s for w in wrong) for s in services), "services": len(services), "wrong": wrong}


def grade_incidents(group, meta, t3):
    remote = os.path.join(group, "remote.git")
    final = meta["final_commit"]
    base = f"projects/{t3['project']}/incidents"
    try:
        index = git(remote, "show", f"{final}:{base}/index.md")
    except subprocess.CalledProcessError:
        index = ""
    rows = [l for l in index.splitlines() if l.startswith("|") and "inc-" in l]
    items = []
    for inc in t3["incidents"]:
        try:
            page = git(remote, "show", f"{final}:{base}/{inc['id']}.md")
        except subprocess.CalledProcessError:
            page = None
        n_rows = sum(inc["id"] in r for r in rows)
        fields = page is not None and all(str(inc[k]) in page for k in ("date", "service", "cause", "minutes"))
        items.append({"id": inc["id"], "agent": inc["agent"], "page": page is not None, "page_fields": fields,
                      "index_rows": n_rows})
    dates = []
    for r in rows:
        m = re.search(r"\d{4}-\d{2}-\d{2}", r)
        dates.append(m.group(0) if m else "")
    new = [i for i in items if i["agent"]]
    return {
        "expected": len(new),
        "pages_missing": sum(not i["page"] for i in new),
        "pages_bad_fields": sum(i["page"] and not i["page_fields"] for i in new),
        "rows_missing": sum(i["index_rows"] == 0 for i in new),
        "rows_duplicated": sum(i["index_rows"] > 1 for i in new),
        "seeded_lost": sum(i["index_rows"] == 0 or not i["page"] for i in items if not i["agent"]),
        "index_sorted": dates == sorted(dates),
        "items": items,
    }


def grade_group(group):
    meta = json.load(open(os.path.join(group, "meta.json")))
    task = meta["task"]
    data = os.path.join(ROOT, "data", "big" if task == "T4" else "small")
    truth = json.load(open(os.path.join(data, "truth.json")))
    out = {k: meta[k] for k in ("group", "task", "cond", "model", "rep")}
    out["sessions"] = {}
    for n, sm in meta["sessions"].items():
        d = os.path.join(group, n)
        out["sessions"][n] = {"exit": sm["exit"], "timed_out": sm["timed_out"], "wall_ms": sm["wall_ms"],
                              "usage": usage(os.path.join(d, "stream.jsonl")),
                              "commands": commands(os.path.join(d, "cmdlog.tsv")),
                              "tools": tool_calls(os.path.join(d, "stream.jsonl"))}
    if task in ("T1", "T4"):
        out["quality"] = grade_values(os.path.join(group, "s1", "work", "answers.json"), truth[task])
    elif task == "T2":
        t = truth["T2"]
        out["quality"] = {"s1": grade_deploy(os.path.join(group, "s1", "work", "answers.json"), t["first"], t["answer"]),
                          "s2": grade_deploy(os.path.join(group, "s2", "work", "answers.json"), t["all"], t["answer"])}
    else:
        out["quality"] = grade_incidents(group, meta, truth["T3"])
    out["wiki"] = wiki_changes(group, meta)
    return out


def main():
    for g in sys.argv[1:]:
        print(json.dumps(grade_group(os.path.abspath(g)), ensure_ascii=False))


if __name__ == "__main__":
    main()
