#!/usr/bin/env python3
"""Questions and answers on real repositories, and the notes wiki.

    gen/real.py

reads the repositories pinned by setup.sh:

  data/remotes/k8s-website.git   kubernetes/website at K8S_COMMIT
  data/remotes/mdn-content.git   mdn/content at MDN_COMMIT

and writes:

  data/real/truth.json           questions and answers of K1, K3, K5, M1, M3 and W
  data/real/notes-wiki.git       the team wiki that K5 and W write to

Every answer is computed from the frontmatter at the pinned commit; the
history is read only to choose questions whose answer changed recently.
"""
import collections
import json
import os
import random
import re
import shutil
import subprocess
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K8S_COMMIT = "aa4e9e6dee49106155072a44ef997b91722243ec"
MDN_COMMIT = "8e307de115d41e9214fcacbd7fe89532756816b4"
K8S = os.path.join(ROOT, "data", "remotes", "k8s-website.git")
MDN = os.path.join(ROOT, "data", "remotes", "mdn-content.git")
GATES = "content/{lang}/docs/reference/command-line-tools-reference/feature-gates/"
SEED = 184


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def read_tree(repo, commit, prefix, suffix=".md"):
    """{path: text} of the files under prefix at commit, in one git process."""
    paths = [p for p in git(repo, "ls-tree", "-r", "--name-only", commit, "--", prefix).splitlines() if p.endswith(suffix)]
    proc = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], input="".join(f"{commit}:{p}\n" for p in paths).encode(),
                          capture_output=True, check=True)
    out, buf, i = {}, proc.stdout, 0
    for p in paths:
        header_end = buf.index(b"\n", i)
        size = int(buf[i:header_end].split()[2])
        out[p] = buf[header_end + 1:header_end + 1 + size].decode("utf-8", "replace")
        i = header_end + 1 + size + 1
    return out


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    try:
        f = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return f if isinstance(f, dict) else {}


def ver(v):
    return str(v).strip().lstrip("v") if v is not None else ""


# ---- Kubernetes feature gates -----------------------------------------------

def gates(lang):
    out = {}
    for path, text in read_tree(K8S, K8S_COMMIT, GATES.format(lang=lang)).items():
        if path.endswith("_index.md"):
            continue
        f = frontmatter(text)
        if not f.get("title"):
            continue
        stages = [{"stage": s.get("stage"), "default": s.get("defaultValue"), "from": ver(s.get("fromVersion")),
                   "to": ver(s.get("toVersion"))} for s in f.get("stages") or [] if isinstance(s, dict)]
        out[f["title"]] = {"path": path, "stages": stages, "removed": "Removed from Kubernetes" in text[:300]}
    return out


def first_from(g, stage):
    vs = [s["from"] for s in g["stages"] if s["stage"] == stage]
    return vs[0] if len(vs) == 1 else None


def version_key(v):
    return tuple(int(x) for x in v.split(".")) if re.fullmatch(r"\d+(\.\d+)*", v) else (0,)


STAGE_WORD = {"alpha": "alpha", "beta": "beta", "stable": "stable（GA）"}


def k1(en, zh, rng):
    """Twelve questions: four on the stage in 1.37 of gates whose Chinese
    translation shows an older stage, four on stages begun in 1.36 or 1.37,
    four on stages begun in 1.30 or before."""
    def q(name, stage, category, stale=None):
        return {"text": f"Kubernetes の feature gate `{name}` が {STAGE_WORD[stage]} の段階に入った版は？（例: `1.30`）",
                "answer": first_from(en[name], stage), "accept": ["v" + first_from(en[name], stage)],
                "stale": stale, "accept_stale": ["v" + stale] if stale else [], "category": category,
                "source": en[name]["path"]}

    def candidates(pred):
        return sorted((n, st) for n, g in en.items() for st in ("alpha", "beta", "stable")
                      if first_from(g, st) and pred(n, g, st))

    def current(g):
        """The stage in effect in 1.37: the last stage whose range reaches it."""
        for st in reversed(g["stages"]):
            if version_key(st["from"]) <= (1, 37) and (not st["to"] or version_key(st["to"]) >= (1, 37)):
                return st["stage"]
        return None

    # A translation that was not updated lacks the newest stages, so its
    # stale value is the stage it still shows as current.
    zh_diff = sorted(n for n, g in en.items() if n in zh and not g["removed"] and current(g)
                     and current(zh[n]) and current(zh[n]) != current(g))
    recent = candidates(lambda n, g, st: first_from(g, st) in ("1.36", "1.37") and n not in zh_diff)
    old = candidates(lambda n, g, st: version_key(first_from(g, st)) <= (1, 30) and not g["removed"] and n not in zh_diff)
    picked, used = [], set()
    for name in rng.sample(zh_diff, 4):
        used.add(name)
        picked.append({"text": f"Kubernetes v1.37 での feature gate `{name}` の段階は？（`alpha`・`beta`・`stable`・`deprecated` のいずれか）",
                       "answer": current(en[name]), "accept": [], "stale": current(zh[name]), "accept_stale": [],
                       "category": "changed_translation", "source": en[name]["path"]})
    for cat, pool, n in (("recent", recent, 4), ("old", old, 4)):
        pool = [c for c in pool if c[0] not in used]
        for name, stage in rng.sample(pool, n):
            used.add(name)
            picked.append(q(name, stage, cat))
    rng.shuffle(picked)
    return {f"q{i + 1:02d}": v for i, v in enumerate(picked)}


def entered(en, stage, version, default=None):
    return sorted(n for n, g in en.items() for s in g["stages"]
                  if s["stage"] == stage and s["from"] == version and (default is None or s["default"] is default))


def k3(en):
    return {
        "a": {"text": "v1.37 で beta の段階に入った feature gate（既定で無効か有効かを問わない）", "answer": entered(en, "beta", "1.37")},
        "b": {"text": "v1.36 で stable（GA）の段階に入った feature gate", "answer": entered(en, "stable", "1.36")},
        "c": {"text": "v1.37 で alpha として追加された feature gate", "answer": entered(en, "alpha", "1.37")},
    }


def k5(en):
    s1 = {"a": {"text": "v1.37 で stable（GA）の段階に入った feature gate", "answer": entered(en, "stable", "1.37")}}
    alpha136 = set(entered(en, "alpha", "1.36"))
    s2 = {
        "a": {"text": "v1.36 で alpha として追加され、v1.37 で beta の段階に入った feature gate",
              "answer": sorted(alpha136 & set(entered(en, "beta", "1.37")))},
        "b": {"text": "v1.37 で、既定で有効（defaultValue が true）な beta の段階に入った feature gate",
              "answer": entered(en, "beta", "1.37", default=True)},
        "c": {"text": "v1.36 で stable（GA）の段階に入った feature gate", "answer": entered(en, "stable", "1.36")},
    }
    return {"s1": s1, "s2": s2}


def w_assign(en, rng, agents=("a", "b", "c"), per_agent=5, seeded=3):
    names = [n for n in sorted(en) if any(s["from"] in ("1.36", "1.37") for s in en[n]["stages"]) and not en[n]["removed"]]
    chosen = rng.sample(names, len(agents) * per_agent + seeded)
    out = []
    for i, n in enumerate(chosen):
        agent = None if i < seeded else agents[(i - seeded) // per_agent]
        out.append({"gate": n, "file": kebab(n) + ".md", "agent": agent, "stages": en[n]["stages"]})
    return out


def kebab(name):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", s)
    return s.lower()


# ---- MDN ------------------------------------------------------------------

STATUSES = ("deprecated", "experimental", "non-standard")


def mdn_pages():
    out = {}
    for path, text in read_tree(MDN, MDN_COMMIT, "files/en-us/").items():
        if not path.endswith("/index.md"):
            continue
        f = frontmatter(text)
        if f.get("slug"):
            out[path] = {"slug": f["slug"], "title": f.get("title"), "page_type": f.get("page-type"),
                         "status": sorted(s for s in f.get("status") or [] if s in STATUSES)}
    return out


def mdn_status_changes(since="2026-01-01"):
    """{path: {"added": set, "removed": set}} of status lines changed since."""
    log = git(MDN, "log", MDN_COMMIT, f"--since={since}", "--format=C %H", "-p", "--unified=0",
              "-G^  - (experimental|deprecated|non-standard)$", "--", "files/en-us/web")
    out = collections.defaultdict(lambda: {"added": set(), "removed": set()})
    path = None
    for line in log.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        m = re.fullmatch(r"([-+])  - (experimental|deprecated|non-standard)", line)
        if m and path:
            out[path]["added" if m.group(1) == "+" else "removed"].add(m.group(2))
    return out


def m1(pages, rng):
    """Twelve questions on the status of a page: five whose status lost a
    value in 2026, four that gained one, three unchanged since 2026."""
    changes = mdn_status_changes()
    lost = sorted(p for p, c in changes.items() if p in pages and c["removed"] - c["added"] and not c["added"])
    gained = sorted(p for p, c in changes.items() if p in pages and c["added"] - c["removed"] and not c["removed"])
    unchanged = sorted(p for p in pages if p not in changes and pages[p]["status"] and p.startswith("files/en-us/web/api/"))
    picked = []
    for cat, pool, n in (("lost_2026", lost, 5), ("gained_2026", gained, 4), ("unchanged", unchanged, 3)):
        for p in rng.sample(pool, n):
            c = changes.get(p, {"added": set(), "removed": set()})
            before = sorted((set(pages[p]["status"]) - c["added"]) | c["removed"]) if cat != "unchanged" else None
            picked.append({"text": f"MDN のページ `{pages[p]['slug']}` の status は？ `deprecated`・`experimental`・`non-standard` のうち当てはまるものをすべて、なければ空の配列で答える",
                           "answer": pages[p]["status"], "stale": before, "category": cat, "source": p})
    rng.shuffle(picked)
    return {f"q{i + 1:02d}": v for i, v in enumerate(picked)}


def m3(pages, rng):
    members = collections.defaultdict(list)
    for p, v in pages.items():
        parts = p.split("/")
        if len(parts) == 7 and parts[2:4] == ["web", "api"]:
            members[parts[4]].append(p)
    ifaces = sorted(i for i, ms in members.items()
                    if 3 <= sum("deprecated" in pages[m]["status"] for m in ms) and 15 <= len(ms) <= 60)
    iface = rng.choice(ifaces)
    iface_slug = pages.get(f"files/en-us/web/api/{iface}/index.md", {}).get("slug", f"Web/API/{iface}")
    return {
        "a": {"text": "CSS プロパティのページ（page-type が `css-property`）のうち、status に `experimental` を含むものの slug",
              "answer": sorted(v["slug"] for v in pages.values() if v["page_type"] == "css-property" and "experimental" in v["status"])},
        "b": {"text": f"`{iface_slug}` の直下のページ（メンバー）のうち、status に `deprecated` を含むものの slug",
              "answer": sorted(pages[m]["slug"] for m in members[iface] if "deprecated" in pages[m]["status"])},
        "c": {"text": "Web API のインターフェイスのページ（page-type が `web-api-interface`）のうち、status に `deprecated` を含むものの slug",
              "answer": sorted(v["slug"] for v in pages.values() if v["page_type"] == "web-api-interface" and "deprecated" in v["status"])},
    }


# ---- notes wiki -------------------------------------------------------------

def gate_page(g):
    rows = "\n".join(f"| {s['stage']} | {str(s['default']).lower()} | {s['from']} | {s['to'] or '-'} |" for s in g["stages"])
    return B.front(f"feature gate {g['gate']} の段階と既定値", "2026-09-01", "observation") + f"""# {g['gate']}

| 段階 | 既定値 | 開始 | 終了 |
|---|---|---|---|
{rows}

## Links
- part_of: [feature gate の一覧](index.md)
- cites: https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/{g['gate']}/
"""


def gate_index(seeded):
    rows = "\n".join(f"| [{g['gate']}]({g['file']}) | {max((s['from'] for s in g['stages']), key=version_key)} |"
                     for g in sorted(seeded, key=lambda g: g["gate"]))
    return B.front("調べた feature gate の一覧（名前の順）", "2026-09-01", "index") + f"""# feature gate の一覧

feature gate ごとにページを作り、この表に 1 行を加える。表は gate の名前の順に並べる。

| gate | 最新の段階の開始 |
|---|---|
{rows}

## Links
- part_of: [kubernetes](../index.md)
"""


def build_notes(out, seeded):
    pages = {
        "global/index.md": B.front("この wiki の構成", "2026-09-01", "index") + """# wiki の構成

- `projects/<name>/`: プロジェクトごとに調べたこと
- `global/`: 全体に関わること
""",
        "projects/kubernetes/index.md": B.front("Kubernetes について調べたこと", "2026-09-01", "index") + """# kubernetes

## Links
- see_also: [feature gate の一覧](feature-gates/index.md)
""",
        "projects/kubernetes/feature-gates/index.md": gate_index(seeded),
    }
    for g in seeded:
        pages[f"projects/kubernetes/feature-gates/{g['file']}"] = gate_page(g)
    work = out + ".work"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    B.git(work, "init", "-q", "-b", "main")
    for rel, text in pages.items():
        B.write(work, rel, text)
    B.git(work, "add", "-A")
    d = "2026-09-01T10:00:00+09:00"
    B.git(work, "commit", "-q", "-m", "wiki を作成する", env={"GIT_AUTHOR_DATE": d, "GIT_COMMITTER_DATE": d})
    shutil.rmtree(out, ignore_errors=True)
    subprocess.run(["git", "clone", "-q", "--bare", work, out], check=True)
    subprocess.run(["git", "-C", out, "remote", "remove", "origin"], check=True)
    shutil.rmtree(work)


def main():
    for repo, commit in ((K8S, K8S_COMMIT), (MDN, MDN_COMMIT)):
        if git(repo, "rev-parse", "HEAD").strip() != commit:
            sys.exit(f"{repo} is not at {commit}; run setup.sh")
    rng = random.Random(SEED)
    en, zh = gates("en"), gates("zh-cn")
    pages = mdn_pages()
    w = w_assign(en, rng)
    truth = {
        "commits": {"kubernetes/website": K8S_COMMIT, "mdn/content": MDN_COMMIT},
        "K1": k1(en, zh, rng), "K3": k3(en), "K5": k5(en),
        "M1": m1(pages, rng), "M3": m3(pages, rng),
        "W": {"dir": "projects/kubernetes/feature-gates", "gates": w},
    }
    out = os.path.join(ROOT, "data", "real")
    os.makedirs(out, exist_ok=True)
    build_notes(os.path.join(out, "notes-wiki.git"), [g for g in w if g["agent"] is None])
    json.dump(truth, open(os.path.join(out, "truth.json"), "w"), ensure_ascii=False, indent=2)
    print(f"gates en={len(en)} zh-cn={len(zh)} mdn pages={len(pages)}")
    for t in ("K3", "M3"):
        print(t, {k: len(v["answer"]) for k, v in truth[t].items()})
    print("K5", {s: {k: len(v["answer"]) for k, v in d.items()} for s, d in truth["K5"].items()})


if __name__ == "__main__":
    main()
