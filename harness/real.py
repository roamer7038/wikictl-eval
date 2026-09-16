"""Groups of the tasks on real repositories (K1, K3, K5, M1, M3, W).

Called from run.py. The documentation repositories are read-only and shared
by every group: data/remotes/k8s-website.git and data/remotes/mdn-content.git.
The notes wiki that K5 and W write to is copied per group to remote.git.

How each condition reaches a documentation repository:

  B0  not at all (the agent answers from its own knowledge), except in K5,
      where B0 reads a clone and only lacks the notes wiki
  B1  a clone made with --shared before the session starts
  B2  wikictl with one profile per repository; the mirror is copied from a
      template made once, so that no condition starts by fetching a
      repository of hundreds of megabytes
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = {"k8s": os.path.join(ROOT, "data", "remotes", "k8s-website.git"),
        "mdn": os.path.join(ROOT, "data", "remotes", "mdn-content.git")}
DOCS_ENV = {"k8s": "K8S_DIR", "mdn": "MDN_DIR"}
TRUTH = os.path.join(ROOT, "data", "real", "truth.json")
NOTES = os.path.join(ROOT, "data", "real", "notes-wiki.git")
MIRRORS = os.path.join(ROOT, "data", "mirrors")

TASKS = {
    "K1": {"conds": ["B0", "B1", "B2"], "sessions": ["s1"], "docs": "k8s", "notes": False},
    "K3": {"conds": ["B0", "B1", "B2"], "sessions": ["s1"], "docs": "k8s", "notes": False},
    "K5": {"conds": ["B0", "B1", "B2"], "sessions": ["s1", "s2"], "docs": "k8s", "notes": True, "b0_reads_docs": True},
    "M1": {"conds": ["B0", "B1", "B2"], "sessions": ["s1"], "docs": "mdn", "notes": False},
    "M3": {"conds": ["B0", "B1", "B2"], "sessions": ["s1"], "docs": "mdn", "notes": False},
    "W": {"conds": ["B1", "B2"], "sessions": ["a", "b", "c"], "docs": "k8s", "notes": True, "concurrent": True},
}


def H():
    import run
    return run


def docs_mode(task, cond):
    if cond == "B2":
        return "wikictl"
    if cond == "B1" or TASKS[task].get("b0_reads_docs"):
        return "clone"
    return "none"


def wikictl_config(path, profiles, default, session):
    lines = [f"default_profile: {default}", "author:", f"  name: agent-{session}",
             f"  email: agent-{session}@example.invalid", "profiles:"]
    for name, repo in profiles.items():
        lines += [f"  {name}:", f"    repo: {repo}"]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def mirror_template(name):
    """The wikictl cache holding the mirror of one documentation repository,
    made once and reused. Returns the directory to use as XDG_CACHE_HOME."""
    tpl = os.path.join(MIRRORS, name)
    os.makedirs(MIRRORS, exist_ok=True)
    with open(os.path.join(MIRRORS, f".{name}.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not os.path.exists(os.path.join(tpl, ".done")):
            shutil.rmtree(tpl, ignore_errors=True)
            os.makedirs(tpl)
            cfg = os.path.join(tpl, "config.yaml")
            wikictl_config(cfg, {name: DOCS[name]}, name, "template")
            subprocess.run([os.path.join(ROOT, "build", "bin", "wikictl"), "--config", cfg, "ls"], check=True,
                           capture_output=True, env={"PATH": "/usr/bin:/bin", "HOME": tpl, "XDG_CACHE_HOME": tpl})
            open(os.path.join(tpl, ".done"), "w").close()
    return tpl


def copy_mirror(name, cache):
    """Copy the template mirror into a session's cache: objects as hard links
    (git never rewrites a pack or loose object in place), the rest as copies."""
    src = os.path.join(mirror_template(name), "wikictl")
    dst = os.path.join(cache, "wikictl")
    os.makedirs(dst, exist_ok=True)
    for entry in os.listdir(src):
        s, d = os.path.join(src, entry), os.path.join(dst, entry)
        if os.path.isdir(s):
            os.makedirs(d)
            for sub in os.listdir(s):
                flag = "-al" if sub == "objects" else "-a"
                subprocess.run(["cp", flag, os.path.join(s, sub), os.path.join(d, sub)], check=True)
        else:
            shutil.copy2(s, d)


def prepare(group, task, cond, session, notes_remote):
    run = H()
    spec = TASKS[task]
    # prepare_session makes the home, wrappers and working directory; the
    # condition "real" keeps it from adding a wiki of the synthetic tasks.
    s = run.prepare_session(group, "real", "real", session, None)
    s["env"], s["add_dirs"] = {}, []
    mode = docs_mode(task, cond)
    # A clone borrows the objects of the pinned repository and a wikictl
    # mirror fetches from it; without either, the jail hides it.
    s["needs_remotes"] = mode != "none"
    docs = spec["docs"]
    fill = {"WORK": s["work"]}
    if mode == "clone":
        d = os.path.join(s["home"], "docs", docs)
        subprocess.run(["git", "clone", "-q", "--shared", DOCS[docs], d], check=True,
                       env={"HOME": s["home"], "PATH": "/usr/bin:/bin"})
        s["env"][DOCS_ENV[docs]] = d
        s["add_dirs"].append(d)
        fill[DOCS_ENV[docs]] = d
    notes_mode = None
    if spec["notes"]:
        notes_mode = {"B0": "none", "B1": "clone", "B2": "wikictl"}[cond]
        if notes_mode == "clone":
            s["wiki_dir"] = os.path.join(s["home"], "wiki")
            subprocess.run(["git", "clone", "-q", notes_remote, s["wiki_dir"]], check=True,
                           env={"HOME": s["home"], "PATH": "/usr/bin:/bin"})
            fill["WIKI_DIR"] = s["wiki_dir"]
    if cond == "B2":
        run.wrap(s["bin"], s["dir"], "wikictl", os.path.join(ROOT, "build", "bin", "wikictl"))
        cfg = os.path.join(s["home"], ".config", "wikictl")
        os.makedirs(cfg, exist_ok=True)
        profiles = {docs: DOCS[docs]}
        if notes_mode == "wikictl":
            profiles["notes"] = notes_remote
        wikictl_config(os.path.join(cfg, "config.yaml"), profiles, "notes" if "notes" in profiles else docs, session)
        copy_mirror(docs, os.path.join(s["home"], ".cache"))
    sources = [read_task(f"src-{mode}-{docs}.md")]
    if notes_mode:
        sources.append(read_task(f"src-{notes_mode}-notes.md"))
    s["sources"] = run.fill("".join(sources).strip(), **fill)
    return s


def read_task(name):
    with open(os.path.join(ROOT, "tasks", name)) as f:
        return f.read()


def prompt(task, cond, session, s, truth):
    run = H()
    env = run.fill(read_task(f"env-real-{cond}.md"), WORK=s["work"], SOURCES=s["sources"])
    if task in ("K1", "M1", "K3", "M3"):
        body = run.fill(read_task(f"{task}.md"),
                        QUESTIONS="\n".join(f"- {k}: {v['text']}" for k, v in truth[task].items()))
    elif task == "K5":
        body = run.fill(read_task(f"K5-{session}.md"),
                        QUESTIONS="\n".join(f"- {k}: {v['text']}" for k, v in truth["K5"][session].items()))
    else:
        gates = [g for g in truth["W"]["gates"] if g["agent"] == session]
        example = next(g for g in truth["W"]["gates"] if g["agent"] is None)["file"]
        body = run.fill(read_task("W.md"), EXAMPLE=example,
                        GATES="\n".join(f"| `{g['gate']}` | `{g['file']}` |" for g in gates))
    return run.fill(read_task("common.md"), ENV=env.strip(), TASK=body.strip()) + "\n"


def main(a):
    run = H()
    spec = TASKS[a.task]
    if a.cond not in spec["conds"]:
        sys.exit(f"{a.task} is not run under {a.cond}")
    token = run.read(os.environ.get("EVAL_TOKEN_FILE", os.path.expanduser("~/.config/wikictl-eval/oauth-token"))).strip()
    truth = json.load(open(TRUTH))
    name = f"{a.task}-{a.cond}-{a.model}-r{a.rep}" + (f"-{a.label}" if a.label else "")
    group = os.path.join(os.path.abspath(a.runs), name)
    os.makedirs(group)
    notes_remote = os.path.join(group, "remote.git")
    if spec["notes"]:
        subprocess.run(["git", "clone", "-q", "--bare", NOTES, notes_remote], check=True)
        subprocess.run(["git", "-C", notes_remote, "remote", "remove", "origin"], check=True)
    meta = {"group": name, "task": a.task, "cond": a.cond, "model": run.MODELS[a.model], "rep": a.rep,
            "versions": run.read(os.path.join(ROOT, "build", "versions.tsv")), "commits": truth["commits"],
            "docs_mode": docs_mode(a.task, a.cond), "sessions": {}}
    if spec["notes"]:
        meta["base_commit"] = run.head(notes_remote)
    if spec.get("concurrent"):
        prepared = {n: prepare(group, a.task, a.cond, n, notes_remote) for n in spec["sessions"]}
        running = {n: run.start(a.model, a.cond, prepared[n], prompt(a.task, a.cond, n, prepared[n], truth), token)
                   for n in spec["sessions"]}
        meta["sessions"].update(run.wait_all(running))
    else:
        for n in spec["sessions"]:
            s = prepare(group, a.task, a.cond, n, notes_remote)
            meta["sessions"][n] = run.wait(run.start(a.model, a.cond, s, prompt(a.task, a.cond, n, s, truth), token))
    if spec["notes"]:
        meta["final_commit"] = run.head(notes_remote)
    json.dump(meta, open(os.path.join(group, "meta.json"), "w"), ensure_ascii=False, indent=2)
    print(json.dumps({n: {k: v for k, v in m.items() if k != "cmd"} for n, m in meta["sessions"].items()}))
