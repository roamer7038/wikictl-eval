#!/usr/bin/env python3
"""Questions and answers of the evaluation, from the pinned repositories.

    gen/tasks.py

reads data/remotes/{k8s-website,k8s-enhancements,mdn-content}.git and
gen/paraphrases.json, and writes data/tasks/truth.json and the notes wiki
data/tasks/notes-wiki.git. The output is deterministic.

A task is one session (P8 two, P9 three) holding questions of these types:

  value  one string; "none" when the thing asked about does not exist
  set    a set of words, compared as a whole (MDN status)
  list   a list of names, graded by F1
"""
import collections
import json
import os
import random
import re
import subprocess
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import real as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTES = os.path.join(ROOT, "data", "remotes")
REPOS = {
    "k8s": {"git": os.path.join(REMOTES, "k8s-website.git"), "commit": R.K8S_COMMIT, "name": "kubernetes/website"},
    "enh": {"git": os.path.join(REMOTES, "k8s-enhancements.git"), "commit": "766deac551650361954ac2f307f9babcdd943b19",
            "name": "kubernetes/enhancements"},
    "mdn": {"git": os.path.join(REMOTES, "mdn-content.git"), "commit": R.MDN_COMMIT, "name": "mdn/content"},
}
OUT = os.path.join(ROOT, "data", "tasks")
SEED = 184


def git(repo, *args):
    return subprocess.run(["git", "-C", REPOS[repo]["git"], *args], capture_output=True, text=True, check=True).stdout


def show(repo, rev, path):
    r = subprocess.run(["git", "-C", REPOS[repo]["git"], "show", f"{rev}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def safe_yaml(text):
    try:
        v = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError):
        return None
    return v if isinstance(v, dict) else None


def body(text):
    m = re.match(r"^---\n.*?\n---\n", text, re.S)
    return text[m.end():] if m else text


def pick(rng, pool, n):
    pool = sorted(pool)
    if len(pool) < n:
        raise SystemExit(f"only {len(pool)} candidates, {n} needed")
    return rng.sample(pool, n)


def value(text, answer, accept=(), stale=None, category=None, source=None):
    return {"type": "value", "text": text, "answer": answer, "accept": sorted(set(accept) - {answer}),
            "stale": stale, "category": category, "source": source}


def listq(text, answer, category=None):
    return {"type": "list", "text": text, "answer": sorted(answer), "category": category}


def number(qs):
    return {f"q{i + 1:02d}": q for i, q in enumerate(qs)}


# ---- shared material --------------------------------------------------------

class K8s:
    def __init__(self):
        self.en = R.gates("en")
        self.zh = R.gates("zh-cn")
        self.docs = R.read_tree(R.K8S, R.K8S_COMMIT, "content/en/docs/")
        self.zh_text = R.read_tree(R.K8S, R.K8S_COMMIT, R.GATES.format(lang="zh-cn"))

    def resolve(self, link):
        link = link.split("#")[0].split("?")[0].rstrip("/")
        for cand in (f"content/en{link}.md", f"content/en{link}/_index.md", f"content/en{link}/index.md"):
            if cand in self.docs:
                return cand
        return None


class Enh:
    def __init__(self):
        self.keps = {}
        for path, text in R.read_tree(REPOS["enh"]["git"], REPOS["enh"]["commit"], "keps/", ".yaml").items():
            if path.endswith("/kep.yaml"):
                k = safe_yaml(text)
                if k:
                    self.keps[path] = k
        self.by_gate = collections.defaultdict(list)
        for path, k in self.keps.items():
            for fg in k.get("feature-gates") or []:
                if isinstance(fg, dict) and isinstance(fg.get("name"), str):
                    self.by_gate[fg["name"]].append(path)


class Mdn:
    def __init__(self):
        self.text = {p: t for p, t in R.read_tree(R.MDN, R.MDN_COMMIT, "files/en-us/").items() if p.endswith("/index.md")}
        self.pages = {}
        for p, t in self.text.items():
            f = R.frontmatter(t)
            if f.get("slug"):
                self.pages[p] = {"slug": f["slug"], "page_type": f.get("page-type"),
                                 "status": sorted(s for s in f.get("status") or [] if s in R.STATUSES)}
        self.by_slug = {v["slug"].lower(): p for p, v in self.pages.items()}


# ---- L: values, with things that do not exist -------------------------------

def current_stages(g, version=(1, 37)):
    return sorted({s["stage"] for s in g["stages"] if s["from"] and R.version_key(s["from"]) <= version
                   and (not s["to"] or R.version_key(s["to"]) >= version)})


def task_l1(k, rng, truth_k1):
    qs = [dict(q, type="value") for q in truth_k1.values()]
    # A gate whose stages overlap in 1.37 (such as beta to 1.37 and stable from
    # 1.37) has no single stage; replace its question with another gate whose
    # translation is out of date, drawn from a generator of its own so that
    # the other tasks keep their questions.
    fix = random.Random(f"{SEED}:l1-overlap")
    used = {q["source"] for q in qs}
    pool = sorted(n for n, g in k.en.items() if n in k.zh and not g["removed"] and len(current_stages(g)) == 1
                  and len(current_stages(k.zh[n])) == 1 and current_stages(k.zh[n]) != current_stages(g)
                  and g["path"] not in used)
    for q in qs:
        if q["category"] == "changed_translation":
            name = re.search(r"`([^`]+)`", q["text"]).group(1)
            if len(current_stages(k.en[name])) != 1:
                new = fix.choice(pool)
                pool.remove(new)
                q.update(text=q["text"].replace(f"`{name}`", f"`{new}`"), answer=current_stages(k.en[new])[0],
                         stale=current_stages(k.zh[new])[0], source=k.en[new]["path"], accept=[])
    for name in ("PodSchedulingReadinessGatesV2", "KubeletSeccompProfileMerge"):
        assert name not in k.en
        qs.append(value(f"Kubernetes v1.37 での feature gate `{name}` の段階は？（`alpha`・`beta`・`stable`・`deprecated` のいずれか）",
                        "none", category="absent"))
    rng.shuffle(qs)
    return number(qs)


def task_l2(m, rng, truth_m1):
    qs = [dict(q, type="set") for q in truth_m1.values()]
    for slug in ("Web/API/Blob/textLines", "Web/API/Navigator/getBatteryLevel"):
        assert slug.lower() not in m.by_slug
        qs.append({"type": "set", "text": f"MDN のページ `{slug}` の status は？ `deprecated`・`experimental`・`non-standard` のうち当てはまるものをすべて、なければ空の配列で答える",
                   "answer": "none", "stale": None, "category": "absent"})
    rng.shuffle(qs)
    return number(qs)


# ---- P2: full-text search ---------------------------------------------------

def task_p2(k, rng):
    occ = collections.defaultdict(set)
    for p, t in k.docs.items():
        for flag in set(re.findall(r"(?<![\w-])--[a-z][a-z0-9]+(?:-[a-z0-9]+){2,}", body(t))):
            occ[flag].add(p)
    cands = [(f, next(iter(ps))) for f, ps in occ.items() if len(ps) == 1 and "/feature-gates/" not in next(iter(ps))]
    qs = [value(f"kubernetes/website の `content/en/docs` の下で、コマンドラインのフラグ `{f}` に触れているただ 1 つのページのパスは？（リポジトリのルートからのパス、例: `content/en/docs/concepts/overview/_index.md`）",
                p, category="fulltext", source=p) for f, p in pick(rng, cands, 8)]
    return number(qs)


# ---- P4: history -------------------------------------------------------------

def merge_date(repo, commit):
    """Committer date of the first-parent commit of main that brought commit in."""
    path = git(repo, "rev-list", "--first-parent", "--ancestry-path", f"{commit}..{REPOS[repo]['commit']}").split()
    return git(repo, "log", "-1", "--format=%cs", path[-1]).strip() if path else None


def first_version_where(repo, path, pred):
    """The oldest commit of path's history (without following renames) whose
    version satisfies pred, when the file's first version does not."""
    log = git(repo, "log", "--format=%H %as %cs", REPOS[repo]["commit"], "--", path).split("\n")
    commits = [l.split() for l in log if l.strip()][::-1]
    if not commits or pred(show(repo, commits[0][0], path) or ""):
        return None
    for h, adate, cdate in commits[1:]:
        if pred(show(repo, h, path) or ""):
            return {"commit": h, "dates": sorted({adate, cdate, merge_date(repo, h) or cdate})}
    return None


def task_p4(k, m, rng):
    def has_stable(text):
        f = R.frontmatter(text)
        return any(isinstance(s, dict) and s.get("stage") == "stable" for s in f.get("stages") or [])

    qs = []
    cands = sorted(n for n, g in k.en.items() if not g["removed"] and R.first_from(g, "stable") in ("1.35", "1.36", "1.37"))
    for name in rng.sample(cands, len(cands)):
        hit = first_version_where("k8s", k.en[name]["path"], has_stable)
        if hit and hit["dates"][0] >= "2025-01-01":
            qs.append(value(f"kubernetes/website で、feature gate `{name}` のページに stable の段階が書き加えられたコミットの日付は？（`YYYY-MM-DD`）",
                            hit["dates"][0], accept=hit["dates"][1:], category="history_k8s", source=k.en[name]["path"]))
        if len(qs) == 4:
            break

    def not_experimental(text):
        return "experimental" not in (R.frontmatter(text).get("status") or []) and bool(R.frontmatter(text))

    changes = R.mdn_status_changes()
    lost = sorted(p for p, c in changes.items() if "experimental" in c["removed"] and "experimental" not in c["added"]
                  and p in m.pages)
    n = 0
    for p in rng.sample(lost, len(lost)):
        hit = first_version_where("mdn", p, not_experimental)
        if hit and hit["dates"][0] >= "2026-01-01":
            qs.append(value(f"mdn/content で、ページ `{m.pages[p]['slug']}` の status から `experimental` が外されたコミットの日付は？（`YYYY-MM-DD`）",
                            hit["dates"][0], accept=hit["dates"][1:], category="history_mdn", source=p))
            n += 1
        if n == 4:
            break
    rng.shuffle(qs)
    return number(qs)


# ---- P5: vague descriptions --------------------------------------------------

def task_p5(k, rng, paraphrases):
    """Gates described without their names: in Japanese, and reworded in
    English (gen/paraphrase.py)."""
    qs = []
    for kind, category, lead in (("k8s_ja", "vague_ja", "次の説明（日本語）"), ("k8s", "vague_en", "次の説明（英語）")):
        for item in paraphrases.get(kind, [])[:5]:
            qs.append(value(f"{lead}に当たる Kubernetes の feature gate の名前（例: `SELinuxMount`）は？\n\n  > {item['text']}",
                            item["gate"], category=category, source=k.en[item["gate"]]["path"]))
    rng.shuffle(qs)
    return number(qs)


# ---- P6: several hops -------------------------------------------------------

def task_p6(k, e, m, rng):
    qs = []
    hops = []
    for n, g in k.en.items():
        mlink = re.search(r"\]\((/docs/[^)\s]+)\)", body(k.docs.get(g["path"], "")))
        tgt = k.resolve(mlink.group(1)) if mlink else None
        title = R.frontmatter(k.docs[tgt]).get("title") if tgt else None
        if title and not g["removed"]:
            hops.append((n, title, tgt))
    for n, title, tgt in pick(rng, hops, 3):
        qs.append(value(f"Kubernetes の文書で、feature gate `{n}` のページの説明文が最初にリンクしている文書のページの title は？",
                        str(title), category="hop_link", source=tgt))

    single = sorted(n for n, ps in e.by_gate.items() if len(ps) == 1 and n in k.en)
    sig_keps = collections.defaultdict(list)
    for p, kep in e.keps.items():
        sig_keps[kep.get("owning-sig")].append(p)

    def stable_137(p):
        kep = e.keps[p]
        return kep.get("stage") == "stable" and R.ver(kep.get("latest-milestone")) == "1.37"

    cands = []
    for n in single:
        kep = e.keps[e.by_gate[n][0]]
        ans = sorted(str(e.keps[p].get("kep-number")) for p in sig_keps[kep.get("owning-sig")] if stable_137(p))
        if 2 <= len(ans) <= 12:
            cands.append((n, kep.get("owning-sig"), ans))
    seen = set()
    for n, sig, ans in rng.sample(cands, len(cands)):
        if sig in seen:
            continue
        seen.add(sig)
        qs.append(listq(f"feature gate `{n}` を導入した KEP（kubernetes/enhancements）の owning-sig が owning-sig である KEP のうち、stage が stable で latest-milestone が v1.37 のものの KEP 番号をすべて",
                        ans, category="hop_kep"))
        if len(seen) == 3:
            break

    def first_ref(text):
        b = body(text)
        mm = re.search(r"\{\{\s*domxref\(\s*\"([^\"]+)\"", b, re.I)
        ml = re.search(r"\]\(", b)
        if not mm or (ml and ml.start() < mm.start()):
            return None
        name = mm.group(1).replace("()", "").replace(".", "/")
        return m.by_slug.get(f"web/api/{name}".lower())

    mh = []
    for p, v in m.pages.items():
        if not p.startswith("files/en-us/web/api/"):
            continue
        tgt = first_ref(m.text[p])
        if tgt and tgt != p and m.pages[tgt]["status"]:
            mh.append((p, tgt))
    for p, tgt in pick(rng, mh, 3):
        qs.append({"type": "set", "text": f"MDN のページ `{m.pages[p]['slug']}` の本文が最初に参照している API のページの status は？ `deprecated`・`experimental`・`non-standard` のうち当てはまるものをすべて、なければ空の配列で答える",
                   "answer": m.pages[tgt]["status"], "stale": None, "category": "hop_mdn", "source": tgt})
    rng.shuffle(qs)
    return number(qs)


# ---- P7: two repositories ----------------------------------------------------

def task_p7(k, e):
    rows = collections.defaultdict(lambda: {"mismatch": [], "missing": []})
    for n, ps in e.by_gate.items():
        if len(ps) != 1 or n not in k.en:
            continue
        kep = e.keps[ps[0]]
        sig = kep.get("owning-sig")
        ms = kep.get("milestone") if isinstance(kep.get("milestone"), dict) else {}
        web = R.first_from(k.en[n], "stable")
        if ms.get("stable") and web and R.ver(ms["stable"]) != web:
            rows[sig]["mismatch"].append(n)
        if kep.get("stage") == "stable" and not any(s["stage"] == "stable" for s in k.en[n]["stages"]):
            rows[sig]["missing"].append(n)
    sig_m = max((s for s in rows if 3 <= len(rows[s]["mismatch"]) <= 12), key=lambda s: (len(rows[s]["mismatch"]), s))
    sig_s = max((s for s in rows if s != sig_m and 2 <= len(rows[s]["missing"]) <= 12), key=lambda s: (len(rows[s]["missing"]), s))
    rule = "（対象は、kubernetes/enhancements の kep.yaml の feature-gates にその名前を挙げる KEP がちょうど 1 つの feature gate に限る）"
    return number([
        listq(f"owning-sig が `{sig_m}` の KEP の feature gate のうち、KEP の milestone.stable の版と、kubernetes/website の feature gate のページで stable の段階が始まる版が異なるもの{rule}",
              rows[sig_m]["mismatch"], category="join_mismatch"),
        listq(f"owning-sig が `{sig_s}` の KEP の feature gate のうち、KEP の stage が stable なのに、kubernetes/website の feature gate のページに stable の段階がないもの{rule}",
              rows[sig_s]["missing"], category="join_missing"),
    ])


# ---- P8: knowledge given only in the first session ---------------------------

PEOPLE = ["aoki", "baba", "chiba", "doi"]
PLANS = ["有効化する", "見送る", "検証する"]


def task_p8(k, rng):
    names = pick(rng, [n for n, g in k.en.items() if not g["removed"] and any(s["from"] in ("1.36", "1.37") for s in g["stages"])], 12)
    decisions = [{"gate": n, "owner": rng.choice(PEOPLE), "plan": rng.choice(PLANS)} for n in names]

    def current(n):
        for st in reversed(k.en[n]["stages"]):
            if R.version_key(st["from"]) <= (1, 37) and (not st["to"] or R.version_key(st["to"]) >= (1, 37)):
                return st["stage"]
        return None

    s1 = number([value(f"feature gate `{d['gate']}` の v1.37 での段階は？（`alpha`・`beta`・`stable`・`deprecated` のいずれか）",
                       current(d["gate"]), category="given") for d in decisions[:4]])
    owner = next(o for o in rng.sample(PEOPLE, len(PEOPLE))
                 if any(d["owner"] == o and current(d["gate"]) == "beta" for d in decisions))
    s2 = number([
        listq(f"チームの判断で担当者が {owner} の feature gate のうち、v1.37 で beta の段階にあるもの",
              [d["gate"] for d in decisions if d["owner"] == owner and current(d["gate"]) == "beta"], category="given_and_docs"),
        listq("チームの判断で「有効化する」とした feature gate のうち、v1.37 で既定で有効（defaultValue が true）なもの",
              [d["gate"] for d in decisions if d["plan"] == "有効化する"
               and any(s["default"] is True and s["from"] and R.version_key(s["from"]) <= (1, 37) and (not s["to"] or R.version_key(s["to"]) >= (1, 37))
                       for s in k.en[d["gate"]]["stages"])], category="given_and_docs"),
        listq("チームの判断で「見送る」とした feature gate", [d["gate"] for d in decisions if d["plan"] == "見送る"], category="given"),
    ])
    return {"decisions": decisions, "s1": s1, "s2": s2}


def p3k_with_alternatives(k, qs):
    """P3K asks which gates "entered" beta in 1.37 and stable in 1.36. The
    answer counts every stage starting then; a reading that leaves out gates
    already in that stage before (only the default changed) is also given as
    an alternative, used by grade/score.py --accept-alternatives."""
    def transitions(stage, version):
        out = []
        for n, g in k.en.items():
            st = g["stages"]
            for i, s in enumerate(st):
                if s["stage"] == stage and s["from"] == version and (i == 0 or st[i - 1]["stage"] != stage):
                    out.append(n)
        return sorted(set(out))
    qs["q01"]["alternatives"] = [transitions("beta", "1.37")]
    qs["q02"]["alternatives"] = [transitions("stable", "1.36")]
    return qs


def main():
    rng = random.Random(SEED)
    for repo, r in REPOS.items():
        if git(repo, "rev-parse", "HEAD").strip() != r["commit"]:
            sys.exit(f"{r['git']} is not at {r['commit']}")
    old = json.load(open(os.path.join(ROOT, "data", "real", "truth.json")))
    paraphrases = json.load(open(os.path.join(ROOT, "gen", "paraphrases.json"))) if os.path.exists(
        os.path.join(ROOT, "gen", "paraphrases.json")) else {}
    k, e, m = K8s(), Enh(), Mdn()
    tasks = {
        "L1": {"sources": ["k8s"], "questions": task_l1(k, rng, old["K1"])},
        "L2": {"sources": ["mdn"], "questions": task_l2(m, rng, old["M1"])},
        "P2": {"sources": ["k8s"], "questions": task_p2(k, rng)},
        "P3K": {"sources": ["k8s"], "questions": p3k_with_alternatives(k, number([dict(v, type="list") for v in old["K3"].values()]))},
        "P3M": {"sources": ["mdn"], "questions": number([dict(v, type="list") for v in old["M3"].values()])},
        "P4": {"sources": ["k8s", "mdn"], "questions": task_p4(k, m, rng)},
        "P5": {"sources": ["k8s"], "questions": task_p5(k, rng, paraphrases)},
        "P6": {"sources": ["k8s", "enh", "mdn"], "questions": task_p6(k, e, m, rng)},
        "P7": {"sources": ["k8s", "enh"], "questions": task_p7(k, e)},
        "P8": dict(task_p8(k, rng), sources=["k8s"], notes=True),
        "P9": {"sources": ["k8s"], "notes": True, "gates": old["W"]["gates"], "dir": old["W"]["dir"]},
    }
    os.makedirs(OUT, exist_ok=True)
    truth = {"commits": {r["name"]: r["commit"] for r in REPOS.values()}, "tasks": tasks}
    json.dump(truth, open(os.path.join(OUT, "truth.json"), "w"), ensure_ascii=False, indent=2)
    R.build_notes(os.path.join(OUT, "notes-wiki.git"), [g for g in old["W"]["gates"] if g["agent"] is None])
    for t, v in tasks.items():
        qs = v.get("questions") or {**v.get("s1", {}), **v.get("s2", {})}
        print(t, len(qs), collections.Counter(q.get("category") or q["type"] for q in qs.values()) if qs else "")


if __name__ == "__main__":
    main()
