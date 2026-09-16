#!/usr/bin/env python3
"""Run agent sessions in Docker.

    harness/eval.py run --task P3K --cond B2 --model sonnet --rep 1 [--delay 40] [--label pilot]
    harness/eval.py batch --tasks L1,P2 --conds B1,B2 --models opus,sonnet,haiku --reps 1 [--label pilot]

A group is one task under one condition, model, delay and repetition, written
to $EVAL_RUNS (default ../wikictl-eval-runs)/<task>-<cond>-<model>-d<delay>-r<rep>[-<label>]/:

  meta.json           versions, commands, exit codes and times
  notes.git           the team wiki of P8 and P9, served by the git server
  <session>/home      HOME: git identity, wikictl config and mirror, the B1 clone of the wiki
  <session>/work      /workspace, with answers.json
  <session>/docs/*    the B1 clones of the documentation repositories
  <session>/bin       the logging wrappers, first on PATH
  <session>/log       cmdlog.tsv of the wrappers
  <session>/prompt.md, stream.jsonl, stderr.txt

Conditions (see CONDS): B0 has no documentation; B1 clones and standard
commands; B2 and its variants wikictl with a plugin. The documentation and
the wiki are served by git daemon containers without delay (git0) or with
a delay of 40 ms on each packet they send (git40).
"""
import argparse
import datetime
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.environ.get("EVAL_RUNS", os.path.join(os.path.dirname(ROOT), "wikictl-eval-runs"))
IMAGE = os.environ.get("EVAL_IMAGE", "wikictl-eval-agent:dev")
GIT_IMAGE = os.environ.get("EVAL_GIT_IMAGE", "wikictl-eval-gitserver:dev")
NETWORK = "wikictl-eval"
TRUTH = os.path.join(ROOT, "data", "tasks", "truth.json")
NOTES = os.path.join(ROOT, "data", "tasks", "notes-wiki.git")
REMOTES = os.path.join(ROOT, "data", "remotes")
TEMPLATES = os.path.join(ROOT, "data", "templates")
TASKS_DIR = os.path.join(ROOT, "tasks", "v2")
TOKEN_FILE = os.environ.get("EVAL_TOKEN_FILE", os.path.expanduser("~/.config/wikictl-eval/oauth-token"))

MODELS = {"opus": "claude-opus-5", "sonnet": "claude-sonnet-5", "haiku": "claude-haiku-4-5"}
REPO_DIRS = {"k8s": "k8s-website", "enh": "k8s-enhancements", "mdn": "mdn-content"}
SESSION_TIMEOUT = 45 * 60
BUDGET_USD = "20"
CPUS, MEMORY = "2", "6g"
BASE_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]

# How a condition reaches the documentation and the wiki, and which wikictl
# and plugin it uses. "nofetch" adds --no-fetch to reads of the documentation.
CONDS = {
    "B0": {"access": "none"},
    "B1": {"access": "clone"},
    "B2": {"access": "wikictl", "wikictl": "release", "plugin": "base"},
    # The description of the skill widened so that it is loaded for any task
    # through wikictl; the body is the base one.
    "B2-trigger": {"access": "wikictl", "wikictl": "release", "plugin": "trigger"},
    # How to read many files, in the top-level help instead of the skill.
    "B2-help": {"access": "wikictl", "wikictl": "help", "plugin": "base"},
    "B2-nofetch": {"access": "wikictl", "wikictl": "release", "plugin": "base", "nofetch": True},
    "B2-skill": {"access": "wikictl", "wikictl": "release", "plugin": "skill"},
    "B2-proto": {"access": "wikictl", "wikictl": "proto", "plugin": "proto", "extensions": True},
    # B2-best with a short skill: the table of commands only, details in help.
    "B2-lean": {"access": "wikictl", "wikictl": "protohelp", "plugin": "lean", "extensions": True, "fetch_ttl": 300},
    "B2-best": {"access": "wikictl", "wikictl": "protohelp", "plugin": "best", "extensions": True, "fetch_ttl": 300},
}

TASK_TEXT = {
    "L1": ("Kubernetes の feature gate について答える", "Kubernetes の文書は英語版（`content/en`）に従う。版は `1.30` の形、段階は `beta` のように語だけを書く。"),
    "L2": ("MDN のページの status を答える", "ページは slug（例: `Web/API/Blob/text`）で示す。status はページの frontmatter に従う。"),
    "P2": ("Kubernetes の文書から記述を探す", ""),
    "P3K": ("Kubernetes の feature gate を集計する", "Kubernetes の文書は英語版（`content/en`）に従う。削除済みの feature gate も含める。feature gate は名前（例: `SELinuxMount`）で書く。"),
    "P3M": ("MDN のページを集計する", "ページは slug（例: `Web/API/Blob/text`）で書く。status と page-type はページの frontmatter に従う。"),
    "P4": ("文書の変更の履歴を調べる", "日付はコミットの日付を `YYYY-MM-DD` の形で書く。"),
    "P5": ("説明から feature gate を特定する", "Kubernetes の文書は英語版（`content/en`）に従う。"),
    "P6": ("文書をたどって答える", "Kubernetes の文書は英語版（`content/en`）に従う。KEP の番号は `1234` の形で書く。"),
    "P7": ("KEP と文書を照合する", "Kubernetes の文書は英語版（`content/en`）に従う。feature gate は名前で書く。"),
}
DATE = "2026-09-16"


def read(path):
    with open(path) as f:
        return f.read()


def fill(text, **kw):
    for k, v in kw.items():
        text = text.replace("{" + k + "}", v)
    return text


def sh(*args, **kw):
    return subprocess.run(list(args), check=True, capture_output=True, text=True, **kw).stdout


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ---- infrastructure ----------------------------------------------------------

def ensure_servers():
    """The network and the two git servers, serving data/remotes and RUNS."""
    os.makedirs(RUNS, exist_ok=True)
    with open(os.path.join(RUNS, ".servers.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _ensure_servers()


def _ensure_servers():
    if subprocess.run(["docker", "network", "inspect", NETWORK], capture_output=True).returncode:
        sh("docker", "network", "create", NETWORK)
    for delay in (0, 40):
        name = f"wikictl-eval-git{delay}"
        r = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}} {{range .Mounts}}{{.Source}};{{end}}", name],
                           capture_output=True, text=True)
        want = {os.path.realpath(REMOTES), os.path.realpath(RUNS)}
        if r.returncode == 0 and r.stdout.startswith("true") and want <= set(r.stdout.split(" ", 1)[1].strip().split(";")):
            continue
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        sh("docker", "run", "-d", "--name", name, "--network", NETWORK, "--network-alias", f"git{delay}",
           "--cap-add", "NET_ADMIN", "-v", f"{REMOTES}:/srv/git/docs:ro", "-v", f"{RUNS}:/srv/git/groups",
           GIT_IMAGE, str(delay))
    time.sleep(1)


def docker_as_agent(args, mounts, env=None, network=True, timeout=None, stdin=None, cpus=CPUS):
    """Preparation outside a session (templates, clones); not measured."""
    cmd = ["docker", "run", "--rm", "-i", "--user", "1000:1000", "--cpus", cpus, "--memory", MEMORY]
    if network:
        cmd += ["--network", NETWORK]
    for src, dst, mode in mounts:
        cmd += ["-v", f"{src}:{dst}:{mode}"]
    for k, v in (env or {}).items():
        cmd += ["-e", f"{k}={v}"]
    return subprocess.run(cmd + [IMAGE, *args], input=stdin, capture_output=True, text=True, timeout=timeout)


def template(kind, repo, delay):
    """A clone (B1) or wikictl mirror cache (B2) of a documentation repository,
    made once through the git server of the delay; returns its directory."""
    name = f"{kind}-{repo}-d{delay}"
    d = os.path.join(TEMPLATES, name)
    os.makedirs(TEMPLATES, exist_ok=True)
    with open(os.path.join(TEMPLATES, f".{name}.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.exists(os.path.join(d, ".done")):
            return d
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        url = f"git://git{delay}/docs/{REPO_DIRS[repo]}.git"
        start = time.time()
        if kind == "search":
            # The index of wikictl-search, built from a copy of the mirror.
            copy_tree(os.path.join(template("mirror", repo, delay), "cache"), os.path.join(d, "cache"))
            os.makedirs(os.path.join(d, "config", "wikictl"))
            with open(os.path.join(d, "config", "wikictl", "config.yaml"), "w") as f:
                f.write(f"repo: {url}\nauthor:\n  name: template\n  email: template@example.invalid\n")
            r = docker_as_agent(["/opt/eval-ext/bin/wikictl-search", "--build-only"], [(d, "/t", "rw")],
                                env={"HOME": "/t", "XDG_CACHE_HOME": "/t/cache", "XDG_CONFIG_HOME": "/t/config",
                                     "PATH": "/opt/wikictl/proto:/usr/local/bin:/usr/bin:/bin"},
                                cpus=str(max(2, (os.cpu_count() or 4) - 6)))
            shutil.rmtree(os.path.join(d, "cache", "wikictl"), ignore_errors=True)
        elif kind == "clone":
            r = docker_as_agent(["git", "clone", "-q", url, "/t/repo"], [(d, "/t", "rw")])
        else:
            with open(os.path.join(d, "config.yaml"), "w") as f:
                f.write(f"repo: {url}\nauthor:\n  name: template\n  email: template@example.invalid\n")
            r = docker_as_agent(["/opt/wikictl/release/wikictl", "--config", "/t/config.yaml", "ls"], [(d, "/t", "rw")],
                                env={"HOME": "/t", "XDG_CACHE_HOME": "/t/cache"})
        if r.returncode:
            raise SystemExit(f"template {name}: {r.stderr}")
        with open(os.path.join(d, ".done"), "w") as f:
            json.dump({"seconds": round(time.time() - start, 1), "url": url, "made": now()}, f)
    return d


def copy_tree(src, dst):
    """Copy a clone or mirror: object files as hard links (git never rewrites
    them in place), everything else as copies."""
    os.makedirs(dst, exist_ok=True)
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target = os.path.join(dst, rel)
        os.makedirs(target, exist_ok=True)
        in_objects = "/objects" in f"/{rel}" or rel.endswith("objects")
        for fn in files:
            s, t = os.path.join(root, fn), os.path.join(target, fn)
            if os.path.islink(s):
                os.symlink(os.readlink(s), t)
            elif in_objects:
                os.link(s, t)
            else:
                shutil.copy2(s, t)


# ---- sessions ----------------------------------------------------------------

def wrapper(name, real, logdir, nofetch_profiles=()):
    text = read(os.path.join(ROOT, "harness", "wrapper.sh.in"))
    text = text.replace("@NAME@", name).replace("@REAL@", real).replace("@LOGDIR@", logdir)
    if nofetch_profiles:
        # Reads of the pinned documentation skip the fetch before reading.
        inject = ("case \" $* \" in\n" + "".join(f"  *\" --profile {p} \"*|*\" --profile={p} \"*) set -- --no-fetch \"$@\" ;;\n"
                                                for p in nofetch_profiles) + "esac\n")
        text = text.replace("real=" + real + "\n", "real=" + real + "\n" + inject, 1)
    return text


def wikictl_config(profiles, default, session):
    lines = [f"default_profile: {default}", "author:", f"  name: agent-{session}",
             f"  email: agent-{session}@example.invalid", "profiles:"]
    for name, repo in profiles.items():
        lines += [f"  {name}:", f"    repo: {repo}"]
    return "\n".join(lines) + "\n"


def prepare(group, task, cond, session, delay, spec):
    c = CONDS[cond]
    d = os.path.join(group, session)
    s = {"dir": d, "mounts": [], "session": session}
    for sub in ("home", "work", "bin", "log"):
        os.makedirs(os.path.join(d, sub))
    home = os.path.join(d, "home")
    open(os.path.join(d, "log", "cmdlog.tsv"), "w").write("time\targv\tstdout_bytes\tstderr_bytes\texit\tms\tcallers\n")
    with open(os.path.join(home, ".gitconfig"), "w") as f:
        f.write(f"[user]\n\tname = agent-{session}\n\temail = agent-{session}@example.invalid\n"
                "[init]\n\tdefaultBranch = main\n[pull]\n\trebase = false\n[safe]\n\tdirectory = *\n")
    for n, real in (("git", "/usr/bin/git"), ("rg", "/usr/bin/rg")):
        open(os.path.join(d, "bin", n), "w").write(wrapper(n, real, "/eval/log"))
    sources = list(spec["sources"])
    access = c["access"]
    # In P8 the condition without a wiki still reads the documentation.
    docs_access = "clone" if access == "none" and spec.get("notes") else access
    notes_url = f"git://git{delay}/groups/{os.path.basename(group)}/notes.git"
    for repo in sources:
        if docs_access == "clone":
            dst = os.path.join(d, "docs", REPO_DIRS[repo])
            copy_tree(os.path.join(template("clone", repo, delay), "repo"), dst)
            s["mounts"].append((dst, f"/docs/{REPO_DIRS[repo]}", "rw"))
    if spec.get("notes") and access == "clone":
        r = docker_as_agent(["git", "clone", "-q", notes_url, "/home/agent/wiki"], [(home, "/home/agent", "rw")],
                            env={"HOME": "/home/agent"})
        if r.returncode:
            raise SystemExit(f"clone notes: {r.stderr}")
    if access == "wikictl":
        real = f"/opt/wikictl/{c['wikictl']}/wikictl"
        open(os.path.join(d, "bin", "wikictl"), "w").write(
            wrapper("wikictl", real, "/eval/log", sources if c.get("nofetch") else ()))
        profiles = {repo: f"git://git{delay}/docs/{REPO_DIRS[repo]}.git" for repo in sources}
        if spec.get("notes"):
            profiles["notes"] = notes_url
        os.makedirs(os.path.join(home, ".config", "wikictl"))
        open(os.path.join(home, ".config", "wikictl", "config.yaml"), "w").write(
            wikictl_config(profiles, "notes" if spec.get("notes") else sources[0], session))
        for repo in sources:
            copy_tree(os.path.join(template("mirror", repo, delay), "cache"), os.path.join(home, ".cache"))
            if c.get("extensions"):
                copy_tree(os.path.join(template("search", repo, delay), "cache"), os.path.join(home, ".cache"))
    for fn in os.listdir(os.path.join(d, "bin")):
        os.chmod(os.path.join(d, "bin", fn), 0o755)
    lines = [read(os.path.join(TASKS_DIR, f"src-{docs_access}-{repo}.md")).strip() for repo in sources]
    if spec.get("notes"):
        lines.append(read(os.path.join(TASKS_DIR, f"src-{ {'none': 'none', 'clone': 'clone', 'wikictl': 'wikictl'}[access]}-notes.md")).strip())
    s["sources"] = "\n".join(lines)
    return s


def questions_text(qs):
    out = []
    for k, q in qs.items():
        text = q["text"].replace("\n\n  > ", "\n\n    > ").replace("\n", "\n  ")
        out.append(f"- {k}: {text}")
    return "\n".join(out)


def prompt(task, cond, s, truth):
    spec = truth["tasks"][task]
    env_name = "B2" if CONDS[cond]["access"] == "wikictl" else ("B1" if CONDS[cond]["access"] == "clone" else "B0")
    env = fill(read(os.path.join(TASKS_DIR, f"env-{env_name}.md")), SOURCES=s["sources"])
    repos = "、".join({"k8s": "kubernetes/website", "enh": "kubernetes/enhancements", "mdn": "mdn/content"}[r]
                      for r in spec["sources"])
    if task == "P9":
        gates = [g for g in spec["gates"] if g["agent"] == s["session"]]
        example = next(g for g in spec["gates"] if g["agent"] is None)["file"]
        body = fill(read(os.path.join(TASKS_DIR, "P9.md")), EXAMPLE=example,
                    GATES="\n".join(f"| `{g['gate']}` | `{g['file']}` |" for g in gates))
    elif task == "P8":
        decisions = "\n".join(f"| `{d['gate']}` | {d['owner']} | {d['plan']} |" for d in spec["decisions"])
        if s["session"] == "s1":
            title = "feature gate についてのチームの判断を受け取り、調べる（1 回目）"
            intro = ("チームは、次の feature gate の扱いを次のように決めた。この表は今回だけ伝える。\n\n"
                     "| feature gate | 担当者 | 判断 |\n|---|---|---|\n" + decisions +
                     "\n\nKubernetes の文書は英語版（`content/en`）に従う。")
            outro = ("この作業は別のセッションで続け、チームの判断と文書の両方を使う別の質問に答える。次のセッションは、この会話も、"
                     "作業ディレクトリへの変更も引き継がない。環境の節に知識の置き場があれば、次のセッションの作業に役立つことを記録しておく。")
        else:
            title = "feature gate についてのチームの判断を使って答える（続き）"
            intro = ("以前のセッションで、いくつかの feature gate についてのチームの判断（担当者と、有効化する・見送る・検証する）を受け取り、"
                     "文書と合わせて調べた。Kubernetes の文書は英語版（`content/en`）に従う。")
            outro = ""
        body = fill(read(os.path.join(TASKS_DIR, "task.md")), TITLE=title, INTRO=intro, REPOS=repos,
                    QUESTIONS=questions_text(spec[s["session"]]), OUTRO=outro)
    else:
        title, intro = TASK_TEXT[task]
        body = fill(read(os.path.join(TASKS_DIR, "task.md")), TITLE=title, INTRO=intro, REPOS=repos,
                    QUESTIONS=questions_text(spec["questions"]), OUTRO="")
    body = re.sub(r"\n{3,}", "\n\n", body)
    common = read(os.path.join(ROOT, "tasks", "common.md"))
    return fill(common, ENV=env.strip(), TASK=body.strip()) + "\n"


def claude_args(model, cond):
    c = CONDS[cond]
    tools = BASE_TOOLS + (["Skill"] if c["access"] == "wikictl" else [])
    args = ["claude", "-p", "--model", MODELS[model], "--output-format", "stream-json", "--verbose",
            "--tools", ",".join(tools), "--allowedTools", ",".join(tools), "--permission-mode", "dontAsk",
            "--strict-mcp-config", "--max-budget-usd", BUDGET_USD,
            "--settings", json.dumps({"autoMemoryEnabled": False}), "--add-dir", "/docs", "--add-dir", "/home/agent",
            "--add-dir", "/tmp"]
    if c["access"] == "wikictl":
        args += ["--plugin-dir", f"/opt/plugin/{c['plugin']}"]
    return args


def start(group, model, cond, s, text, token):
    d = s["dir"]
    open(os.path.join(d, "prompt.md"), "w").write(text)
    c = CONDS[cond]
    path = "/eval/bin" + (":/opt/eval-ext/bin" if c.get("extensions") else "") + ":/usr/local/bin:/usr/bin:/bin"
    name = f"eval-{os.path.basename(group)}-{s['session']}"[:120]
    cmd = ["docker", "run", "--rm", "-i", "--name", name, "--user", "1000:1000", "--cpus", CPUS, "--memory", MEMORY,
           "--network", NETWORK, "-w", "/workspace",
           "-e", "HOME=/home/agent", "-e", f"PATH={path}", "-e", "CLAUDE_CONFIG_DIR=/home/agent/.claude-eval",
           "-e", "CLAUDE_CODE_OAUTH_TOKEN", "-e", "TZ=UTC", "-e", "LANG=C.UTF-8", "-e", "DISABLE_AUTOUPDATER=1",
           "-e", "GIT_TERMINAL_PROMPT=0", "-e", f"WIKICTL_FETCH_TTL={c.get('fetch_ttl', '')}",
           "-v", f"{d}/home:/home/agent:rw", "-v", f"{d}/work:/workspace:rw", "-v", f"{d}/bin:/eval/bin:ro",
           "-v", f"{d}/log:/eval/log:rw"]
    for src, dst, mode in s["mounts"]:
        cmd += ["-v", f"{src}:{dst}:{mode}"]
    cmd += [IMAGE, *claude_args(model, cond)]
    out = open(os.path.join(d, "stream.jsonl"), "w")
    err = open(os.path.join(d, "stderr.txt"), "w")
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=out, stderr=err, text=True,
                         env={**os.environ, "CLAUDE_CODE_OAUTH_TOKEN": token})
    p.stdin.write(text)
    p.stdin.close()
    return {"proc": p, "name": name, "cmd": [x for x in cmd if not x.startswith("CLAUDE_CODE_OAUTH_TOKEN=")],
            "started": time.time(), "started_at": now()}


def wait_all(running):
    done = {}
    while len(done) < len(running):
        for n, r in running.items():
            if n in done:
                continue
            timed_out = time.time() - r["started"] > SESSION_TIMEOUT
            if r["proc"].poll() is not None or timed_out:
                if timed_out:
                    subprocess.run(["docker", "kill", r["name"]], capture_output=True)
                rc = r["proc"].wait()
                done[n] = {"started_at": r["started_at"], "wall_ms": int((time.time() - r["started"]) * 1000),
                           "exit": rc, "timed_out": timed_out, "cmd": r["cmd"]}
        time.sleep(0.5)
    return {n: done[n] for n in running}


def rate_limited(stream):
    """Whether the session ended on a usage or rate limit rather than on its own."""
    try:
        lines = open(stream).read().splitlines()
    except FileNotFoundError:
        return False
    for line in reversed(lines):
        try:
            j = json.loads(line)
        except ValueError:
            continue
        if j.get("type") == "result":
            text = json.dumps(j).lower()
            return bool(j.get("is_error")) and bool(re.search(r"rate.?limit|usage limit|429|overloaded|quota", text))
    return False


def reset_wait(group):
    """Seconds until the limit named in a session's result resets, such as
    "resets 5pm (UTC)" or "resets 5:30am (UTC)", plus two minutes; None when
    the result names no time of day."""
    for n in os.listdir(group):
        stream = os.path.join(group, n, "stream.jsonl")
        if not os.path.exists(stream):
            continue
        m = re.search(r"resets (\d{1,2})(?::(\d{2}))?\s*(am|pm) \(UTC\)", open(stream).read())
        if m:
            hour = int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0)
            t = datetime.datetime.now(datetime.timezone.utc)
            at = t.replace(hour=hour, minute=int(m.group(2) or 0), second=0, microsecond=0)
            if at <= t:
                at += datetime.timedelta(days=1)
            return (at - t).total_seconds() + 120
    return None


def git_head(group):
    r = subprocess.run(["git", "-C", os.path.join(group, "notes.git"), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or None


def run_group(task, cond, model, rep, delay, label=""):
    truth = json.load(open(TRUTH))
    spec = truth["tasks"][task]
    if cond == "B0" and task not in ("L1", "L2", "P8"):
        raise SystemExit(f"{task} is not run under B0")
    if task == "P9" and cond == "B0":
        raise SystemExit("P9 is not run under B0")
    token = read(TOKEN_FILE).strip()
    ensure_servers()
    name = f"{task}-{cond}-{model}-d{delay}-r{rep}" + (f"-{label}" if label else "")
    group = os.path.join(RUNS, name)
    os.makedirs(group)
    if spec.get("notes"):
        sh("git", "clone", "-q", "--bare", NOTES, os.path.join(group, "notes.git"))
        sh("git", "-C", os.path.join(group, "notes.git"), "remote", "remove", "origin")
        sh("git", "-C", os.path.join(group, "notes.git"), "config", "daemon.receivepack", "true")
    image_id = sh("docker", "image", "inspect", "-f", "{{.Id}}", IMAGE).strip()
    meta = {"group": name, "task": task, "cond": cond, "model": MODELS[model], "rep": rep, "delay_ms": delay,
            "image": IMAGE, "image_id": image_id, "commits": truth["commits"], "sessions": {},
            "base_commit": git_head(group) if spec.get("notes") else None}
    sessions = {"P8": ["s1", "s2"], "P9": ["a", "b", "c"]}.get(task, ["s1"])
    if task == "P9":
        prepared = {n: prepare(group, task, cond, n, delay, spec) for n in sessions}
        running = {n: start(group, model, cond, prepared[n], prompt(task, cond, prepared[n], truth), token) for n in sessions}
        meta["sessions"].update(wait_all(running))
    else:
        for n in sessions:
            s = prepare(group, task, cond, n, delay, spec)
            r = start(group, model, cond, s, prompt(task, cond, s, truth), token)
            meta["sessions"].update(wait_all({n: r}))
    meta["final_commit"] = git_head(group) if spec.get("notes") else None
    meta["rate_limited"] = any(rate_limited(os.path.join(group, n, "stream.jsonl")) for n in sessions)
    json.dump(meta, open(os.path.join(group, "meta.json"), "w"), ensure_ascii=False, indent=2)
    return name, meta


# ---- batch -------------------------------------------------------------------

def batch(a):
    tasks, conds, models = a.tasks.split(","), a.conds.split(","), a.models.split(",")
    log = open(os.path.join(RUNS, f"batch-{a.label or 'main'}.log"), "a")
    lock = threading.Lock()

    def say(msg):
        with lock:
            log.write(f"{now()} {msg}\n")
            log.flush()

    jobs = {m: [] for m in models}
    for rep in range(a.first_rep, a.first_rep + a.reps):
        for t in tasks:
            for c in conds:
                if c == "B0" and t not in ("L1", "L2", "P8"):
                    continue
                for m in models:
                    jobs[m].append((t, c, m, rep))
    lanes = [[] for _ in range(a.lanes)]
    for i, m in enumerate(models):
        lanes[i % a.lanes].extend(jobs[m])
    pause = {"until": 0.0}

    def lane(items):
        for t, c, m, rep in items:
            name = f"{t}-{c}-{m}-d{a.delay}-r{rep}" + (f"-{a.label}" if a.label else "")
            group = os.path.join(RUNS, name)
            if os.path.exists(os.path.join(group, "meta.json")):
                meta = json.load(open(os.path.join(group, "meta.json")))
                if not meta.get("rate_limited"):
                    say(f"skip {name}")
                    continue
            for attempt in range(20):
                while time.time() < pause["until"]:
                    time.sleep(30)
                if os.path.exists(group):
                    os.makedirs(os.path.join(RUNS, "_retried"), exist_ok=True)
                    shutil.move(group, os.path.join(RUNS, "_retried", f"{name}-{int(time.time())}"))
                say(f"start {name} attempt={attempt}")
                try:
                    _, meta = run_group(t, c, m, rep, a.delay, a.label)
                except Exception as e:  # noqa: BLE001
                    say(f"error {name} {e!r}")
                    break
                summary = {n: (v["exit"], v["wall_ms"]) for n, v in meta["sessions"].items()}
                say(f"done {name} {summary} rate_limited={meta['rate_limited']}")
                if not meta["rate_limited"]:
                    break
                wait = reset_wait(group) or min(3600, 600 * 2 ** attempt)
                with lock:
                    pause["until"] = max(pause["until"], time.time() + wait)
                say(f"rate limited; pausing all lanes for {wait}s")

    threads = [threading.Thread(target=lane, args=(l,)) for l in lanes if l]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    say("batch finished")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--task", required=True)
    r.add_argument("--cond", required=True, choices=sorted(CONDS))
    r.add_argument("--model", required=True, choices=sorted(MODELS))
    r.add_argument("--rep", type=int, required=True)
    r.add_argument("--delay", type=int, default=40, choices=[0, 40])
    r.add_argument("--label", default="")
    b = sub.add_parser("batch")
    b.add_argument("--tasks", required=True)
    b.add_argument("--conds", required=True)
    b.add_argument("--models", required=True)
    b.add_argument("--reps", type=int, default=1)
    b.add_argument("--first-rep", type=int, default=1)
    b.add_argument("--delay", type=int, default=40, choices=[0, 40])
    b.add_argument("--lanes", type=int, default=3)
    b.add_argument("--label", default="")
    p = sub.add_parser("prompt", help="print the prompt of a session without running it")
    p.add_argument("--task", required=True)
    p.add_argument("--cond", required=True, choices=sorted(CONDS))
    p.add_argument("--session", default="s1")
    a = ap.parse_args()
    if a.cmd == "run":
        name, meta = run_group(a.task, a.cond, a.model, a.rep, a.delay, a.label)
        print(json.dumps({"group": name, "rate_limited": meta["rate_limited"],
                          "sessions": {n: {k: v for k, v in m.items() if k != "cmd"} for n, m in meta["sessions"].items()}}))
    elif a.cmd == "batch":
        ensure_servers()
        batch(a)
    else:
        truth = json.load(open(TRUTH))
        spec = truth["tasks"][a.task]
        srcs = [read(os.path.join(TASKS_DIR, f"src-{('clone' if CONDS[a.cond]['access'] == 'none' and spec.get('notes') else CONDS[a.cond]['access'])}-{r}.md")).strip()
                for r in spec["sources"]]
        print(prompt(a.task, a.cond, {"sources": "\n".join(srcs), "session": a.session}, truth))


if __name__ == "__main__":
    main()
