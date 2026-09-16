#!/usr/bin/env python3
"""Run one group of agent sessions: one task, condition, model and repetition.

    harness/run.py --task T1 --cond B2 --model haiku --rep 1

A group is written to runs/<task>-<cond>-<model>-r<rep>/:

  remote.git/           the wiki the sessions read and write (B1, B2; T3 always)
  meta.json             versions, commands, exit codes and times
  <session>/
    prompt.md           the prompt given to claude
    home/               HOME (git identity, wikictl config and mirror, the B1 clone)
    claude/             CLAUDE_CONFIG_DIR (the transcript)
    work/               the working directory (answers.json)
    bin/                logging wrappers put first on PATH
    cmdlog.tsv          commands the agent ran through the wrappers
    stream.jsonl        claude -p --output-format stream-json
    stderr.txt

Sessions of T1 and T4 are one session; T2 runs s1 then s2, each with a fresh
working directory; T3 starts agents a, b and c at the same time.

Authentication: CLAUDE_CODE_OAUTH_TOKEN, read from $EVAL_TOKEN_FILE
(default ~/.config/wikictl-eval/oauth-token), made with "claude setup-token".
"""
import argparse
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gen"))
import build as B  # noqa: E402

MODELS = {"opus": "claude-opus-5", "sonnet": "claude-sonnet-5", "haiku": "claude-haiku-4-5"}
CONDS = {"T1": ["B0", "B1", "B2"], "T2": ["B0", "B1", "B2"], "T3": ["B1", "B2"], "T4": ["B1", "B2"]}
SESSION_TIMEOUT = 45 * 60
BUDGET_USD = "15"
# Outside any Git repository: Claude Code puts the git status of an enclosing
# repository into the system prompt.
RUNS = os.environ.get("EVAL_RUNS", os.path.join(os.path.dirname(ROOT), "wikictl-eval-runs"))
BASE_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]


def read(path):
    with open(path) as f:
        return f.read()


def fill(text, **kw):
    for k, v in kw.items():
        text = text.replace("{" + k + "}", v)
    return text


def prompt(task, cond, session, s, truth):
    env = fill(read(os.path.join(ROOT, "tasks", f"env-{cond}.md")), WORK=s["work"], WIKI_DIR=s.get("wiki_dir", ""))
    if task in ("T1", "T4"):
        qs = truth[task]
        body = fill(read(os.path.join(ROOT, "tasks", "T1.md")),
                    QUESTIONS="\n".join(f"- {k}: {v['text']}" for k, v in qs.items()))
    elif task == "T2":
        t = truth["T2"]
        projects = []
        for svc in t["all"]:
            p = svc.split("-")[0]
            if p not in projects:
                projects.append(p)
        body = fill(read(os.path.join(ROOT, "tasks", f"T2-{session}.md")),
                    FIRST="、".join(B.T2_FIRST), ALL="、".join(projects))
    else:
        rows = [i for i in truth["T3"]["incidents"] if i["agent"] == session]
        body = fill(read(os.path.join(ROOT, "tasks", "T3.md")), INCIDENTS="\n".join(
            f"| {i['id']} | {i['date']} | {i['service']} | {i['cause']} | {i['minutes']} |" for i in rows))
    return fill(read(os.path.join(ROOT, "tasks", "common.md")), ENV=env.strip(), TASK=body.strip()) + "\n"


def wrap(bindir, logdir, name, real):
    text = read(os.path.join(ROOT, "harness", "wrapper.sh.in"))
    text = text.replace("@NAME@", name).replace("@REAL@", shlex.quote(real)).replace("@LOGDIR@", logdir)
    path = os.path.join(bindir, name)
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, 0o755)


def prepare_session(group, task, cond, session, remote):
    d = os.path.join(group, session)
    s = {"dir": d, "home": os.path.join(d, "home"), "claude": os.path.join(d, "claude"),
         "work": os.path.join(d, "work"), "bin": os.path.join(d, "bin"), "tmp": os.path.join(d, "tmp")}
    for k in ("home", "claude", "work", "bin", "tmp"):
        os.makedirs(s[k])
    open(os.path.join(d, "cmdlog.tsv"), "w").write("time\targv\tstdout_bytes\tstderr_bytes\texit\tms\tcallers\n")
    with open(os.path.join(s["home"], ".gitconfig"), "w") as f:
        f.write(f"[user]\n\tname = agent-{session}\n\temail = agent-{session}@example.invalid\n"
                "[init]\n\tdefaultBranch = main\n[pull]\n\trebase = false\n")

    data = os.path.join(ROOT, "data", "big" if task == "T4" else "small")
    if task in ("T1", "T4"):
        shutil.copytree(os.path.join(data, "infra"), os.path.join(s["work"], "infra"))
    elif task == "T2":
        shutil.copytree(os.path.join(data, "deploy"), os.path.join(s["work"], "deploy"))

    wrap(s["bin"], d, "git", shutil.which("git", path="/usr/bin:/bin"))
    wrap(s["bin"], d, "rg", shutil.which("rg", path="/usr/local/bin:/usr/bin:/bin"))
    if cond == "B1":
        s["wiki_dir"] = os.path.join(s["home"], "wiki")
        subprocess.run(["git", "clone", "-q", remote, s["wiki_dir"]], check=True,
                       env={"HOME": s["home"], "PATH": "/usr/bin:/bin"})
    if cond == "B2":
        wrap(s["bin"], d, "wikictl", os.path.join(ROOT, "build", "bin", "wikictl"))
        cfg = os.path.join(s["home"], ".config", "wikictl")
        os.makedirs(cfg)
        with open(os.path.join(cfg, "config.yaml"), "w") as f:
            f.write(f"repo: {remote}\nauthor:\n  name: agent-{session}\n  email: agent-{session}@example.invalid\n")
    return s


def command(model, cond, s):
    tools = BASE_TOOLS + (["Skill"] if cond == "B2" else [])
    cmd = ["claude", "-p", "--model", MODELS[model], "--output-format", "stream-json", "--verbose",
           "--tools", ",".join(tools), "--allowedTools", ",".join(tools), "--permission-mode", "dontAsk",
           "--strict-mcp-config", "--max-budget-usd", BUDGET_USD,
           "--settings", json.dumps({"autoMemoryEnabled": False}),
           "--add-dir", s["tmp"]]
    for d in [s.get("wiki_dir")] + s.get("add_dirs", []):
        if d:
            cmd += ["--add-dir", d]
    if cond == "B2":
        cmd += ["--plugin-dir", os.path.join(ROOT, "build", "plugin")]
    return cmd


def environment(s, token):
    env = {"HOME": s["home"], "PATH": f"{s['bin']}:/usr/local/bin:/usr/bin:/bin", "TERM": "dumb",
           "LANG": "C.UTF-8", "TMPDIR": s["tmp"], "CLAUDE_CONFIG_DIR": s["claude"],
           "CLAUDE_CODE_OAUTH_TOKEN": token, "XDG_CONFIG_HOME": os.path.join(s["home"], ".config"),
           "XDG_CACHE_HOME": os.path.join(s["home"], ".cache"), "GIT_TERMINAL_PROMPT": "0",
           "DISABLE_AUTOUPDATER": "1"}
    if "wiki_dir" in s:
        env["WIKI_DIR"] = s["wiki_dir"]
    env.update(s.get("env", {}))
    return env


def jailed(s, argv):
    """argv run in harness/jail.sh, which sees only the session's group
    directory (read-write) and the programs and pinned repositories
    (read-only)."""
    group = os.path.dirname(s["dir"])
    ro = [os.path.realpath(shutil.which("claude")), os.path.join(ROOT, "build", "bin", "wikictl"),
          os.path.join(ROOT, "build", "plugin")]
    if s.get("needs_remotes"):
        ro.append(os.path.join(ROOT, "data", "remotes"))
    # On WSL /etc/resolv.conf links to /mnt/wsl/resolv.conf, which the jail hides.
    resolv = os.path.realpath("/etc/resolv.conf")
    if resolv.startswith(("/home/", "/tmp/", "/mnt/")):
        ro.append(resolv)
    return ["unshare", "-Urmpf", "--mount-proc", os.path.join(ROOT, "harness", "jail.sh"), s["work"], group, "--",
            *ro, "--", *argv]


def start(model, cond, s, text, token):
    with open(os.path.join(s["dir"], "prompt.md"), "w") as f:
        f.write(text)
    claude = os.path.realpath(shutil.which("claude"))
    cmd = command(model, cond, s)
    out = open(os.path.join(s["dir"], "stream.jsonl"), "w")
    err = open(os.path.join(s["dir"], "stderr.txt"), "w")
    p = subprocess.Popen(jailed(s, [claude, *cmd[1:]]), cwd=s["work"], env=environment(s, token),
                         stdin=subprocess.PIPE, stdout=out, stderr=err, text=True)
    p.stdin.write(text)
    p.stdin.close()
    return {"proc": p, "cmd": cmd, "started": time.time(),
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def wait_all(running):
    """Wait for sessions started at the same time, taking each one's wall time
    when it ends rather than when the ones before it end."""
    done = {}
    while len(done) < len(running):
        for n, r in running.items():
            if n in done:
                continue
            if r["proc"].poll() is not None or time.time() - r["started"] > SESSION_TIMEOUT:
                done[n] = wait(r)
        time.sleep(0.5)
    return {n: done[n] for n in running}


def wait(r):
    try:
        rc = r["proc"].wait(timeout=max(1, SESSION_TIMEOUT - (time.time() - r["started"])))
        timed_out = False
    except subprocess.TimeoutExpired:
        r["proc"].kill()
        rc = r["proc"].wait()
        timed_out = True
    return {"cmd": r["cmd"], "started_at": r["started_at"], "wall_ms": int((time.time() - r["started"]) * 1000),
            "exit": rc, "timed_out": timed_out}


def head(remote):
    return subprocess.run(["git", "-C", remote, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=sorted(CONDS) + sorted(R.TASKS))
    ap.add_argument("--cond", required=True, choices=["B0", "B1", "B2"])
    ap.add_argument("--model", required=True, choices=sorted(MODELS))
    ap.add_argument("--rep", required=True, type=int)
    ap.add_argument("--runs", default=RUNS)
    ap.add_argument("--label", default="", help="suffix of the group name, e.g. pilot")
    a = ap.parse_args()
    if a.task in R.TASKS:
        return R.main(a)
    if a.cond not in CONDS[a.task]:
        sys.exit(f"{a.task} is not run under {a.cond}")
    token_file = os.environ.get("EVAL_TOKEN_FILE", os.path.expanduser("~/.config/wikictl-eval/oauth-token"))
    token = read(token_file).strip()

    name = f"{a.task}-{a.cond}-{a.model}-r{a.rep}" + (f"-{a.label}" if a.label else "")
    group = os.path.join(os.path.abspath(a.runs), name)
    os.makedirs(group)
    data = os.path.join(ROOT, "data", "big" if a.task == "T4" else "small")
    truth = json.load(open(os.path.join(data, "truth.json")))
    remote = os.path.join(group, "remote.git")
    subprocess.run(["git", "clone", "-q", "--bare", os.path.join(data, "wiki.git"), remote], check=True)
    subprocess.run(["git", "-C", remote, "remote", "remove", "origin"], check=True)

    meta = {"group": name, "task": a.task, "cond": a.cond, "model": MODELS[a.model], "rep": a.rep,
            "versions": read(os.path.join(ROOT, "build", "versions.tsv")), "base_commit": head(remote),
            "sessions": {}}
    sessions = {"T1": ["s1"], "T4": ["s1"], "T2": ["s1", "s2"], "T3": B.T3_AGENTS}[a.task]
    if a.task == "T3":
        prepared = {n: prepare_session(group, a.task, a.cond, n, remote) for n in sessions}
        running = {n: start(a.model, a.cond, prepared[n], prompt(a.task, a.cond, n, prepared[n], truth), token)
                   for n in sessions}
        meta["sessions"].update(wait_all(running))
    else:
        for n in sessions:
            s = prepare_session(group, a.task, a.cond, n, remote)
            meta["sessions"][n] = wait(start(a.model, a.cond, s, prompt(a.task, a.cond, n, s, truth), token))
            meta["sessions"][n]["remote_head_after"] = head(remote)
    meta["final_commit"] = head(remote)
    json.dump(meta, open(os.path.join(group, "meta.json"), "w"), ensure_ascii=False, indent=2)
    print(json.dumps({n: {k: v for k, v in m.items() if k != "cmd"} for n, m in meta["sessions"].items()}))


sys.path.insert(0, os.path.join(ROOT, "harness"))
import real as R  # noqa: E402

if __name__ == "__main__":
    main()
