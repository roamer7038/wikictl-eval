#!/usr/bin/env python3
"""Score the groups written by harness/eval.py.

    grade/score.py <group-dir>... > scores.jsonl

One JSON object per group with:

  quality   per question: verdict (value, set) or precision/recall/F1 (list);
            score = mean over questions of 1 (correct) / 0 or F1; success =
            every question correct (F1 >= 0.95 counting as correct);
            for P9 the pages and rows recorded
  cost      USD and tokens from the result event of each session
  time      wall time, API time and the time spent in tools
  calls     tool calls from the transcript, with the Bash commands split
            into programs (wikictl subcommands separately), each with its
            count, seconds and output bytes
"""
import json
import os
import re
import shlex
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "grade"))
import grade as G  # noqa: E402

TRUTH = os.path.join(ROOT, "data", "tasks", "truth.json")
F1_OK = 0.95


# ---- quality -----------------------------------------------------------------

def norm(v):
    return G.norm(v)


ACCEPT_ALTERNATIVES = False


def f1_of(got, want):
    tp = len(got & want)
    p = tp / len(got) if got else float(not want)
    r = tp / len(want) if want else 1.0
    return 2 * p * r / (p + r) if p + r else 0.0


def score_question(q, a):
    t = q["type"]
    if t == "value":
        if isinstance(a, list) and len(a) == 1:
            a = a[0]
        if a is None:
            return {"verdict": "unknown", "score": 0.0}
        if not isinstance(a, (str, int, float)):
            return {"verdict": "wrong", "score": 0.0}
        if norm(a) in {norm(x) for x in [q["answer"], *q.get("accept", [])]}:
            return {"verdict": "correct", "score": 1.0}
        if q.get("stale") is not None and norm(a) == norm(q["stale"]):
            return {"verdict": "stale", "score": 0.0}
        return {"verdict": "wrong", "score": 0.0}
    if t == "set":
        if a is None:
            return {"verdict": "unknown", "score": 0.0}
        if q["answer"] == "none" or a == "none":
            ok = q["answer"] == "none" and isinstance(a, str) and norm(a) == "none"
            return {"verdict": "correct" if ok else "wrong", "score": float(ok)}
        if not isinstance(a, list):
            return {"verdict": "wrong", "score": 0.0}
        got = sorted({norm(x) for x in a if x is not None})
        if got == sorted(norm(x) for x in q["answer"]):
            return {"verdict": "correct", "score": 1.0}
        if q.get("stale") is not None and got == sorted(norm(x) for x in q["stale"]):
            return {"verdict": "stale", "score": 0.0}
        return {"verdict": "wrong", "score": 0.0}
    if a is None:
        return {"verdict": "unknown", "score": 0.0}
    if not isinstance(a, list):
        return {"verdict": "wrong", "score": 0.0}
    got = {norm(x) for x in a if x is not None}
    answers = [q["answer"]] + (q.get("alternatives", []) if ACCEPT_ALTERNATIVES else [])
    want = max(({norm(x) for x in ans} for ans in answers), key=lambda w: f1_of(got, w))
    tp = len(got & want)
    p = tp / len(got) if got else float(not want)
    r = tp / len(want) if want else 1.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"verdict": "correct" if f1 >= F1_OK else "partial" if f1 > 0 else "wrong", "score": round(f1, 3),
            "precision": round(p, 3), "recall": round(r, 3), "missing": sorted(want - got), "extra": sorted(got - want)}


def score_answers(path, qs):
    try:
        ans = json.load(open(path))
        err = None if isinstance(ans, dict) else "not an object"
    except FileNotFoundError:
        ans, err = {}, "missing"
    except ValueError as e:
        ans, err = {}, f"invalid: {e}"
    if not isinstance(ans, dict):
        ans = {}
    # Groups of the first pilot were asked P3K and P3M with the keys a, b and c.
    for old, new in (("a", "q01"), ("b", "q02"), ("c", "q03")):
        if new not in ans and old in ans:
            ans[new] = ans[old]
    items = {}
    for k, q in qs.items():
        items[k] = dict(score_question(q, ans.get(k)), category=q.get("category"), type=q["type"])
    scores = [i["score"] for i in items.values()]
    verdicts = [i["verdict"] for i in items.values()]
    by_cat = {}
    for i in items.values():
        c = by_cat.setdefault(i["category"] or i["type"], {"n": 0, "score": 0.0})
        c["n"] += 1
        c["score"] += i["score"]
    return {"answers_error": err, "items": items, "score": round(sum(scores) / len(scores), 3) if scores else None,
            "success": all(v == "correct" for v in verdicts),
            "counts": {v: verdicts.count(v) for v in ("correct", "partial", "stale", "unknown", "wrong")},
            "by_category": {c: round(v["score"] / v["n"], 3) for c, v in by_cat.items()}}


def score_p9(group, meta, spec):
    q = G.grade_gate_notes(group.replace("notes.git", ""), {"final_commit": meta["final_commit"]},
                           {"dir": spec["dir"], "gates": spec["gates"]}) if meta.get("final_commit") else None
    return q


# ---- transcript --------------------------------------------------------------

KEYWORDS = {"do", "done", "then", "fi", "if", "elif", "else", "while", "until", "!", "{", "}"}
BUILTINS = {"echo", "printf", "cd", "set", "export", "true", "false", "test", "[", "[[", "local", "read", "return",
            "break", "continue", "in", "esac", "shift", "wait", "exit", ":"}
PROGRAM_SPLIT = re.compile(r"\|\||&&|[|;&\n()]|\$\(|`")


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")


def strip_heredocs(command):
    """The command without the bodies of its here-documents."""
    lines, out, end = command.split("\n"), [], None
    for line in lines:
        if end is not None:
            if line.strip() == end:
                end = None
            continue
        out.append(line)
        m = HEREDOC.search(line)
        if m:
            end = m.group(2)
    return "\n".join(out)


def programs(command):
    """The programs a Bash command names, with wikictl split by subcommand.
    A command in a loop counts once; the wrappers' logs count executions."""
    out = []
    command = strip_heredocs(command)
    for part in PROGRAM_SPLIT.split(command):
        try:
            words = shlex.split(part, comments=True)
        except ValueError:
            words = part.split()
        while words and (re.match(r"^\w+=", words[0]) or words[0] in KEYWORDS or words[0] in (
                "sudo", "time", "env", "xargs", "command", "exec", "nice", "timeout")):
            words = words[1:]
            while words and words[0].startswith("-"):
                words = words[1:]
        if not words:
            continue
        prog = os.path.basename(words[0])
        if prog in BUILTINS or words[0] in ("for", "case"):
            continue
        if prog.startswith("wikictl"):
            rest = [w for w in words[1:] if not w.startswith("-")]
            flags_with_value = {"--profile", "--config"}
            i = 1
            while i < len(words):
                if words[i] in flags_with_value:
                    if i + 1 < len(words) and words[i + 1] in rest:
                        rest.remove(words[i + 1])
                    i += 2
                    continue
                i += 1
            prog = f"{prog} {rest[0]}" if rest else prog
        elif prog == "git":
            rest = [w for w in words[1:] if not w.startswith("-")]
            if "-C" in words:
                idx = words.index("-C")
                if idx + 1 < len(words) and words[idx + 1] in rest:
                    rest.remove(words[idx + 1])
            prog = f"git {rest[0]}" if rest else "git"
        out.append(prog)
    return out


# Ways of reading that the variants of B2 add, counted in the Bash commands.
FEATURES = {
    "meta": r"wikictl[^\n|;]*\smeta\b",
    "log": r"wikictl[^\n|;]*\slog\b",
    "show": r"wikictl[^\n|;]*\sshow\s",
    "snapshot": r"wikictl[^\n|;]*\ssnapshot\b",
    "search": r"wikictl-search\b",
    "no_fetch": r"--no-fetch",
    "many_paths": r"xargs[^\n]*wikictl[^\n]*\s(cat|stat|ls)\b",
}

VIOLATIONS = {
    # Reading the documentation or the wiki around wikictl, which B2 forbids.
    "wikictl_mirror": re.compile(r"\.cache/wikictl\b|GIT_DIR="),
    "direct_git_remote": re.compile(r"\bgit\s+(-C\s+\S+\s+)?clone\b|git://"),
    "network": re.compile(r"\b(curl|wget)\b"),
}


def violations(commands, cond):
    """Commands that break the rules of the prompt, by kind."""
    out = {}
    for c in commands:
        for kind, rx in VIOLATIONS.items():
            if kind in ("wikictl_mirror", "direct_git_remote") and not cond.startswith("B2"):
                continue
            if rx.search(c):
                out[kind] = out.get(kind, 0) + 1
    return out


def transcript(home, cond=""):
    """Tool calls of a session from its transcript, timed by the timestamps
    of the call and of its result."""
    base = os.path.join(home, ".claude-eval", "projects")
    files = []
    for root, _, fs in os.walk(base):
        files += [os.path.join(root, f) for f in fs if f.endswith(".jsonl")]
    calls, results = {}, {}
    for fn in files:
        for line in open(fn):
            try:
                j = json.loads(line)
            except ValueError:
                continue
            ts = j.get("timestamp")
            msg = j.get("message") or {}
            for c in msg.get("content") or [] if isinstance(msg.get("content"), list) else []:
                if c.get("type") == "tool_use":
                    calls[c["id"]] = {"name": c["name"], "input": c.get("input") or {}, "ts": ts}
                elif c.get("type") == "tool_result":
                    content = c.get("content")
                    size = len(json.dumps(content, ensure_ascii=False).encode()) if not isinstance(content, str) else len(content.encode())
                    results[c.get("tool_use_id")] = {"ts": ts, "bytes": size, "error": bool(c.get("is_error"))}
    tools, progs = {}, {}
    total_tool_s = 0.0
    for cid, c in calls.items():
        r = results.get(cid, {})
        secs = seconds(c["ts"], r.get("ts"))
        total_tool_s += secs
        t = tools.setdefault(c["name"], {"n": 0, "s": 0.0, "bytes": 0, "errors": 0})
        t["n"] += 1
        t["s"] += secs
        t["bytes"] += r.get("bytes", 0)
        t["errors"] += r.get("error", False)
        if c["name"] == "Bash":
            ps = programs(c["input"].get("command", "")) or ["(shell)"]
            for p in set(ps):
                e = progs.setdefault(p, {"calls": 0, "in_commands": 0, "s": 0.0, "bytes": 0})
                e["calls"] += ps.count(p)
                e["in_commands"] += 1
                e["s"] += secs / len(set(ps))
                e["bytes"] += r.get("bytes", 0) // len(set(ps))
        if c["name"] == "Skill":
            s = tools.setdefault("Skill:" + str(c["input"].get("skill") or c["input"].get("command")), {"n": 0, "s": 0.0, "bytes": 0, "errors": 0})
            s["n"] += 1
    for d in list(tools.values()) + list(progs.values()):
        d["s"] = round(d["s"], 1)
    commands = [c["input"].get("command", "") for c in calls.values() if c["name"] == "Bash"]
    text = "\n".join(strip_heredocs(c) for c in commands)
    order = sorted(calls.values(), key=lambda c: c["ts"] or "")
    first_skill = next((i + 1 for i, c in enumerate(order) if c["name"] == "Skill"), None)
    return {"tools": tools, "programs": progs, "tool_seconds": round(total_tool_s, 1),
            "tool_calls": sum(v["n"] for k, v in tools.items() if ":" not in k),
            "violations": violations(commands, cond),
            "skill": {"loaded": first_skill is not None, "first_call": first_skill,
                      "help_calls": len(re.findall(r"wikictl[^\n|;]*\bhelp\b", text))},
            "features": {k: len(re.findall(p, text)) for k, p in FEATURES.items()}}


def seconds(a, b):
    if not a or not b:
        return 0.0
    import datetime
    fa = datetime.datetime.fromisoformat(a.replace("Z", "+00:00"))
    fb = datetime.datetime.fromisoformat(b.replace("Z", "+00:00"))
    return max(0.0, (fb - fa).total_seconds())


def executions(group, meta):
    """Runs of wikictl (by subcommand), git and rg logged by the wrappers,
    without the git that Claude Code runs itself."""
    out = {}
    for n in meta["sessions"]:
        path = os.path.join(group, n, "log", "cmdlog.tsv")
        if not os.path.exists(path):
            continue
        for row in G.csv.DictReader(open(path), delimiter="\t", quoting=G.csv.QUOTE_NONE):
            if not G.by_agent(row):
                continue
            prog = (programs(row["argv"]) or ["?"])[0]
            e = out.setdefault(prog, {"runs": 0, "s": 0.0, "bytes": 0, "failed": 0})
            e["runs"] += 1
            e["s"] = round(e["s"] + int(row["ms"]) / 1000, 1)
            e["bytes"] += int(row["stdout_bytes"])
            e["failed"] += row["exit"] != "0"
    return out


def result_event(stream):
    res = None
    for line in open(stream):
        try:
            j = json.loads(line)
        except ValueError:
            continue
        if j.get("type") == "result":
            res = j
    return res


# ---- group -------------------------------------------------------------------

def score_group(group):
    meta = json.load(open(os.path.join(group, "meta.json")))
    truth = json.load(open(TRUTH))
    task = meta["task"]
    spec = truth["tasks"][task]
    out = {k: meta.get(k) for k in ("group", "task", "cond", "model", "rep", "delay_ms", "rate_limited")}
    sessions = {}
    for n, sm in meta["sessions"].items():
        d = os.path.join(group, n)
        u = G.usage(os.path.join(d, "stream.jsonl"))
        res = result_event(os.path.join(d, "stream.jsonl")) or {}
        sessions[n] = {"exit": sm["exit"], "timed_out": sm["timed_out"], "wall_s": round(sm["wall_ms"] / 1000, 1),
                       "api_s": round((res.get("duration_api_ms") or 0) / 1000, 1), "turns": res.get("num_turns"),
                       "usd": u.get("usd"), "tokens": {k: u.get(k) for k in ("input", "output", "cache_read", "cache_write")},
                       "is_error": u.get("is_error"), "complete": u.get("complete"),
                       **transcript(os.path.join(d, "home"), meta["cond"])}
    out["sessions"] = sessions
    if task == "P9":
        out["quality"] = G.grade_gate_notes(group, meta, {"dir": spec["dir"], "gates": spec["gates"]})
        q = out["quality"]
        q["success"] = not any(q[k] for k in ("pages_missing", "pages_bad_facts", "rows_missing", "rows_duplicated",
                                              "seeded_lost")) and q["index_sorted"]
        q["score"] = round(1 - (q["pages_missing"] + q["pages_bad_facts"] + q["rows_missing"] + q["rows_duplicated"])
                           / (2 * q["expected"]), 3)
    elif task == "P8":
        s1 = score_answers(os.path.join(group, "s1", "work", "answers.json"), spec["s1"])
        s2 = score_answers(os.path.join(group, "s2", "work", "answers.json"), spec["s2"])
        out["quality"] = {"s1": s1, "s2": s2, "score": s2["score"], "success": s2["success"]}
    else:
        out["quality"] = score_answers(os.path.join(group, "s1", "work", "answers.json"), spec["questions"])
    if meta.get("base_commit"):
        out["wiki"] = G.wiki_changes_repo(os.path.join(group, "notes.git"), meta["base_commit"], meta["final_commit"], group)
    out["usd"] = round(sum(s["usd"] or 0 for s in sessions.values()), 4)
    out["wall_s"] = round(sum(s["wall_s"] for s in sessions.values()) if task != "P9"
                          else max(s["wall_s"] for s in sessions.values()), 1)
    out["tool_calls"] = sum(s["tool_calls"] for s in sessions.values())
    out["executions"] = executions(group, meta)
    out["violations"] = {}
    for s in sessions.values():
        for k, v in s["violations"].items():
            out["violations"][k] = out["violations"].get(k, 0) + v
    return out


def main():
    global ACCEPT_ALTERNATIVES
    args = sys.argv[1:]
    if args and args[0] == "--accept-alternatives":
        # Also accept the alternative answers of a question (P3K), as a
        # sensitivity check on how the question was worded.
        ACCEPT_ALTERNATIVES = True
        args = args[1:]
    for g in args:
        if os.path.exists(os.path.join(g, "meta.json")):
            print(json.dumps(score_group(os.path.abspath(g)), ensure_ascii=False))


if __name__ == "__main__":
    main()
