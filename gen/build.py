#!/usr/bin/env python3
"""Build the data sets of the evaluation from the world model.

    gen/build.py <out-dir>

writes, under <out-dir>:

  small/wiki.git       the wiki of about 70 pages, with its history (T1, T2, T3)
  small/infra/         configuration files of the services and hosts (T1)
  small/deploy/        the deploy repository with layered values (T2)
  small/truth.json     answers of T1, T2 and T3
  big/wiki.git         the same wiki with filler projects and machines, about 1,000 pages (T4)
  big/infra/
  big/truth.json       answers of T4 (the questions of T1)

The output is deterministic: commit dates, authors and file order are fixed.
"""
import copy
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world as W  # noqa: E402

AUTHOR = {"GIT_AUTHOR_NAME": "wiki-seed", "GIT_AUTHOR_EMAIL": "wiki-seed@example.invalid",
          "GIT_COMMITTER_NAME": "wiki-seed", "GIT_COMMITTER_EMAIL": "wiki-seed@example.invalid"}


def git(cwd, *args, env=None):
    e = {"PATH": os.environ["PATH"], "HOME": cwd, "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"}
    e.update(AUTHOR)
    if env:
        e.update(env)
    return subprocess.run(["git", *args], cwd=cwd, env=e, check=True, capture_output=True, text=True).stdout


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def front(summary, updated, type_=None):
    lines = ["---", f"summary: {summary}"]
    if type_:
        lines.append(f"type: {type_}")
    lines += [f"updated: {updated}", "---", ""]
    return "\n".join(lines)


# ---- wiki pages ------------------------------------------------------------

def page_global_index(state):
    return front("この wiki の構成と、各ディレクトリに置くもの", W.BASE_DATE, "index") + """# wiki の構成

- `machines/<name>/`: マシンごとの構成（OS、ドライバ、バックアップ先）
- `projects/<name>/`: プロジェクトごとのサービス、決定、定例の議事録、手順
- `global/`: 全体に関わること

同じことについて複数のページで値が食い違うときは、frontmatter の `updated` が新しいページの記述を現在の値とする。

## Links
- see_also: [メンバー](people.md)
"""


def page_people(state):
    rows = "\n".join(f"| {p['name']} | {p['team']} |" for p in state["people"])
    return front("メンバーと所属するチーム", W.BASE_DATE, "index") + f"""# メンバー

| 名前 | チーム |
|---|---|
{rows}

## Links
- part_of: [wiki の構成](index.md)
"""


def page_machine(state, m, updated):
    return front(f"{m['name']} の構成（OS、GPU ドライバ、バックアップ先、SSH ポート）", updated, "observation") + f"""# {m['name']}

| 項目 | 値 |
|---|---|
| OS | {m['os']} |
| NVIDIA ドライバ | {m['driver']} |
| バックアップ先 | {m['backup']} |
| SSH ポート | {m['ssh_port']} |

## Links
- part_of: [wiki の構成](../../global/index.md)
"""


def page_project(state, p):
    svcs = "\n".join(f"- [{s['name']}](services/{s['name']}.md)" for s in p["services"])
    return front(f"{p['name']} プロジェクトの概要（サービス、リード、決定）", W.BASE_DATE, "index") + f"""# {p['name']}

リード: {p['lead']}

## サービス

{svcs}

## Links
- see_also: [ジョブキューの選定](decisions/0001-queue.md)
- see_also: [本番へのデプロイ](runbook.md)
"""


def page_service(state, p, s, updated):
    return front(f"{s['name']} の稼働するマシン、ポート、PostgreSQL の版、担当", updated, "observation") + f"""# {s['name']}

| 項目 | 値 |
|---|---|
| 稼働するマシン | [{s['host']}](../../../machines/{s['host']}/index.md) |
| ポート | {s['port']} |
| PostgreSQL | {s['postgres']} |
| 担当 | {s['owner']} |

本番へのデプロイは [手順](../runbook.md) を参照。

## Links
- part_of: [{p['name']}](../index.md)
"""


def page_runbook(state, p):
    body = "\n".join(f"## {s['name']}\n\n```sh\n{s['deploy']}\n```\n" for s in p["services"])
    return front(f"{p['name']} のサービスを本番へデプロイするコマンド", W.BASE_DATE, "procedure") + f"""# {p['name']} の本番へのデプロイ

{body}
## Links
- part_of: [{p['name']}](index.md)
"""


def page_decision(state, p, updated):
    others = "、".join(q for q in W.QUEUES if q != p["queue"])
    return front(f"{p['name']} のジョブキューに {p['queue']} を使う決定", updated, "decision") + f"""# ジョブキューの選定

- 採用: {p['queue']}
- 理由: {W.QUEUE_REASONS[p['queue']]}
- 検討したもの: {others}

## Links
- part_of: [{p['name']}](../index.md)
"""


MEETING_LINE = {
    "driver": "{name} の NVIDIA ドライバは {old} のまま運用する。",
    "backup": "{name} のバックアップ先は {old} とする。",
    "port": "{name} のポートは {old} で公開している。",
    "owner": "{name} の担当は {old}。",
    "postgres": "{name} の PostgreSQL は {old} を使う。",
    "queue": "ジョブキューは {old} で進める。",
}


def page_meeting(p, date, changes):
    lines = "\n".join("- " + MEETING_LINE[c["key"]].format(name=c["name"], old=c["old"]) for c in changes)
    return front(f"{p} の定例の議事録（{date}）", date, "event") + f"""# {p} 定例 {date}

{lines}
- 次回までに監視のダッシュボードを見直す。

## Links
- part_of: [{p}](../index.md)
"""


def render_wiki(state, updated):
    """All pages of the wiki except the meeting notes, from the current state."""
    pages = {"global/index.md": page_global_index(state), "global/people.md": page_people(state)}
    for m in state["machines"]:
        pages[f"machines/{m['name']}/index.md"] = page_machine(state, m, updated[("machine", m["name"])])
    for p in state["projects"]:
        base = f"projects/{p['name']}"
        pages[f"{base}/index.md"] = page_project(state, p)
        pages[f"{base}/runbook.md"] = page_runbook(state, p)
        pages[f"{base}/decisions/0001-queue.md"] = page_decision(state, p, updated[("project", p["name"])])
        for s in p["services"]:
            pages[f"{base}/services/{s['name']}.md"] = page_service(state, p, s, updated[("service", s["name"])])
    return pages


def build_wiki(world, out, extra_pages=None):
    """Write the wiki as a bare repository whose history holds the changes."""
    work = out + ".work"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    git(work, "init", "-q", "-b", "main")

    state = copy.deepcopy(world)
    for c in world["changes"]:
        W.find(state, c["kind"], c["name"])[c["key"]] = c["old"]
    updated = {("machine", m["name"]): W.BASE_DATE for m in world["machines"]}
    updated.update({("project", p["name"]): W.BASE_DATE for p in world["projects"]})
    updated.update({("service", s["name"]): W.BASE_DATE for p in world["projects"] for s in p["services"]})

    def commit(date, message, pages):
        for rel, text in pages.items():
            write(work, rel, text)
        git(work, "add", "-A")
        d = f"{date}T10:00:00+09:00"
        git(work, "commit", "-q", "-m", message, env={"GIT_AUTHOR_DATE": d, "GIT_COMMITTER_DATE": d})

    commit(W.BASE_DATE, "wiki を作成する", render_wiki(state, updated))
    notes = {}
    for c in world["changes"]:
        notes.setdefault((c["project"], c["note_date"]), []).append(c)
    events = [(date, 0, ("note", p, date)) for (p, date) in notes]
    events += [(c["updated"], 1, ("update", c)) for c in world["changes"]]
    for date, _, ev in sorted(events, key=lambda e: (e[0], e[1], json.dumps(e[2], sort_keys=True))):
        if ev[0] == "note":
            _, p, d = ev
            commit(d, f"{p} の定例の議事録を追加する", {f"projects/{p}/meetings/{d}.md": page_meeting(p, d, notes[(p, d)])})
        else:
            c = ev[1]
            W.find(state, c["kind"], c["name"])[c["key"]] = c["new"]
            updated[(c["kind"], c["name"])] = max(updated[(c["kind"], c["name"])], c["updated"])
            commit(c["updated"], f"{c['name']} の {c['key']} を更新する", render_wiki(state, updated))
    if extra_pages:
        for date, message, pages in extra_pages:
            commit(date, message, pages)
    shutil.rmtree(out, ignore_errors=True)
    subprocess.run(["git", "clone", "-q", "--bare", work, out], check=True)
    subprocess.run(["git", "-C", out, "remote", "remove", "origin"], check=True)
    shutil.rmtree(work)
    return state


# ---- workspaces ------------------------------------------------------------

def build_infra(world, root):
    shutil.rmtree(root, ignore_errors=True)
    write(root, "README.md", """# infra

本番環境の構成ファイル。

- `hosts/<name>.yaml`: マシンの OS と SSH ポート
- `services/<service>.yaml`: サービスの稼働するマシン、公開するポート、PostgreSQL のイメージ
""")
    for m in world["machines"]:
        write(root, f"hosts/{m['name']}.yaml", f"name: {m['name']}\nos: \"{m['os']}\"\nssh:\n  port: {m['ssh_port']}\n")
    for p in world["projects"]:
        for s in p["services"]:
            write(root, f"services/{s['name']}.yaml",
                  f"service: {s['name']}\nproject: {p['name']}\nhost: {s['host']}\n"
                  f"expose:\n  - {s['port']}\ndatabase:\n  image: postgres:{s['postgres']}\n")


def yaml_values(vals, indent="  "):
    out = []
    for k in ("replicas", "memory", "port"):
        if k in vals:
            v = vals[k]
            out.append(f"{indent}{k}: {json.dumps(v) if isinstance(v, str) else v}")
    return "\n".join(out)


def build_deploy(world, root):
    shutil.rmtree(root, ignore_errors=True)
    write(root, "README.md", """# deploy

サービスの配置の設定。本番（prod）での値は、次の順に重ねて決まる。後のものが前のものを上書きする。

1. `base/<kind>.yaml` の `values`。`extends` があれば、その kind の値を先に適用する（再帰的に）
2. `services/<project>/<service>.yaml` の `values`（`kind` で 1 の kind を選ぶ）
3. `envs/prod/<project>.yaml` の `values`（そのプロジェクトのすべてのサービス）
4. `envs/prod/services/<service>.yaml` の `values`（ファイルがあるサービスだけ）

キーは `replicas`（整数）、`memory`（文字列）、`port`（整数）。
""")
    for k, d in W.DEPLOY_KINDS.items():
        ext = f"extends: {d['extends']}\n" if d["extends"] else ""
        write(root, f"base/{k}.yaml", f"kind: {k}\n{ext}values:\n{yaml_values(d['values'])}\n")
    for p in world["projects"]:
        write(root, f"envs/prod/{p['name']}.yaml",
              f"project: {p['name']}\nvalues:{(chr(10) + yaml_values(p['env_prod'])) if p['env_prod'] else ' {}'}\n")
        for s in p["services"]:
            o = s["deploy_overrides"]
            write(root, f"services/{p['name']}/{s['name']}.yaml",
                  f"service: {s['name']}\nkind: {W.ROLE_KIND[s['role']]}\n"
                  f"values:{(chr(10) + yaml_values(o['service'])) if o['service'] else ' {}'}\n")
            if o["env_service"]:
                write(root, f"envs/prod/services/{s['name']}.yaml",
                      f"service: {s['name']}\nvalues:\n{yaml_values(o['env_service'])}\n")


# ---- questions and answers -------------------------------------------------

def t1_questions(world):
    """Ten questions on the core entities; the same questions are asked in T4."""
    changed = {(c["kind"], c["name"], c["key"]) for c in world["changes"]}
    core_p = [p for p in world["projects"] if p["name"] in W.CORE_PROJECTS]
    core_s = [s for p in core_p for s in p["services"]]
    core_m = [m for m in world["machines"] if m["name"] in W.CORE_MACHINES]

    def pick(items, kind, key):
        for it in items:
            if (kind, it["name"], key) in changed:
                return it
        return items[0]

    team = {p["name"]: p["team"] for p in world["people"]}
    m1 = pick(core_m, "machine", "driver")
    m2 = pick([m for m in core_m if m is not m1], "machine", "backup")
    m3 = core_m[-1]
    s1 = pick(core_s, "service", "port")
    s2 = pick([s for s in core_s if s is not s1], "service", "postgres")
    s3 = pick([s for s in core_s if s not in (s1, s2)], "service", "owner")
    p1 = pick(core_p, "project", "queue")
    s4 = core_s[5]
    s5 = next(s for s in core_s if s["host"] != m2["name"] and ("machine", s["host"], "backup") in changed) \
        if any(("machine", s["host"], "backup") in changed for s in core_s) else core_s[7]
    s6 = core_s[10]
    hm = W.find(world, "machine", s5["host"])

    def q(text, answer, kind, name, key, sources):
        stale = _str(W.old_value(world, kind, name, key))
        # A version may be written as the image tag of infra/, which also
        # holds it.
        prefix = {"postgres": "postgres:"}.get(key, "")
        return {"text": text, "answer": str(answer), "stale": stale, "sources": sources,
                "accept": [prefix + str(answer)] if prefix else [],
                "accept_stale": [prefix + stale] if prefix and stale else []}

    qs = [
        q(f"マシン {m1['name']} の NVIDIA ドライバの版は？", m1["driver"], "machine", m1["name"], "driver", ["wiki"]),
        q(f"マシン {m2['name']} のバックアップ先は？", m2["backup"], "machine", m2["name"], "backup", ["wiki"]),
        q(f"マシン {m3['name']} の OS（ディストリビューションと版）は？", m3["os"], "machine", m3["name"], "os", ["wiki", "infra"]),
        q(f"サービス {s1['name']} が公開するポートは？", s1["port"], "service", s1["name"], "port", ["wiki", "infra"]),
        q(f"サービス {s2['name']} が使う PostgreSQL の版は？", s2["postgres"], "service", s2["name"], "postgres", ["wiki", "infra"]),
        q(f"サービス {s3['name']} の担当者の名前は？", s3["owner"], "service", s3["name"], "owner", ["wiki"]),
        q(f"プロジェクト {p1['name']} のジョブキューに採用しているものは？", p1["queue"], "project", p1["name"], "queue", ["wiki"]),
        q(f"サービス {s4['name']} を本番へデプロイするコマンドは？", s4["deploy"], "service", s4["name"], "deploy", ["wiki"]),
        q(f"サービス {s5['name']} が稼働するマシンのバックアップ先は？", hm["backup"], "machine", hm["name"], "backup", ["wiki"]),
        q(f"サービス {s6['name']} の担当者が所属するチームは？", team[s6["owner"]], "service", s6["name"], "owner", ["wiki"]),
    ]
    # The stale value of the last question is the team of the old owner.
    old_owner = W.old_value(world, "service", s6["name"], "owner")
    qs[-1]["stale"] = team[old_owner] if old_owner and team[old_owner] != team[s6["owner"]] else None
    return {f"q{i + 1:02d}": v for i, v in enumerate(qs)}


def _str(v):
    return None if v is None else str(v)


T2_FIRST = ["alpha", "bravo", "charlie", "delta"]

T3_PROJECT = "alpha"
T3_AGENTS = ["a", "b", "c"]
T3_CAUSES = ["証明書の期限切れ", "ディスクの枯渇", "設定の誤り", "依存サービスの停止", "メモリ不足",
             "DNS の設定の誤り", "マイグレーションの失敗", "キューの滞留"]


def t3_incidents(world):
    import random
    r = random.Random(f"{world['seed']}:t3")
    p = W.find(world, "project", T3_PROJECT)
    out = []
    for i in range(3 + 5 * len(T3_AGENTS)):
        s = r.choice(p["services"])
        out.append({"id": f"inc-2026-{i + 1:03d}", "date": W._date(90 + i * 2), "service": s["name"],
                    "cause": r.choice(T3_CAUSES), "minutes": r.randint(5, 180),
                    "agent": None if i < 3 else T3_AGENTS[(i - 3) // 5]})
    return out


def incident_page(inc):
    return front(f"{inc['date']} の {inc['service']} の障害（{inc['cause']}、{inc['minutes']} 分）", inc["date"], "event") + f"""# {inc['id']}

- 発生日: {inc['date']}
- サービス: {inc['service']}
- 原因: {inc['cause']}
- 影響時間: {inc['minutes']} 分

## Links
- part_of: [障害の一覧](index.md)
"""


def incident_index(incs):
    rows = "\n".join(f"| [{i['id']}]({i['id']}.md) | {i['date']} | {i['service']} | {i['cause']} |" for i in incs)
    return front(f"{T3_PROJECT} の障害の一覧", incs[-1]["date"], "index") + f"""# {T3_PROJECT} の障害の一覧

障害ごとにページを作り、この表に 1 行を加える。

| ID | 発生日 | サービス | 原因 |
|---|---|---|---|
{rows}

## Links
- part_of: [{T3_PROJECT}](../index.md)
"""


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "data")
    small = W.make_world()
    big = W.make_world(projects=130, machines=100)

    d = os.path.join(out, "small")
    os.makedirs(d, exist_ok=True)
    incs = t3_incidents(small)
    seeded = [i for i in incs if i["agent"] is None]
    extra = [(seeded[-1]["date"], f"{T3_PROJECT} の障害の一覧を作る",
              {**{f"projects/{T3_PROJECT}/incidents/{i['id']}.md": incident_page(i) for i in seeded},
               f"projects/{T3_PROJECT}/incidents/index.md": incident_index(seeded)})]
    build_wiki(small, os.path.join(d, "wiki.git"), extra)
    build_infra(small, os.path.join(d, "infra"))
    build_deploy(small, os.path.join(d, "deploy"))
    services = [s["name"] for p in small["projects"] for s in p["services"]]
    truth = {
        "T1": t1_questions(small),
        "T2": {"first": [s for s in services if W.project_of(small, s)["name"] in T2_FIRST],
               "all": services,
               "answer": {s: W.effective_deploy(small, s) for s in services}},
        "T3": {"project": T3_PROJECT, "incidents": incs},
    }
    json.dump(truth, open(os.path.join(d, "truth.json"), "w"), ensure_ascii=False, indent=2)
    json.dump(small, open(os.path.join(d, "world.json"), "w"), ensure_ascii=False, indent=2)

    d = os.path.join(out, "big")
    os.makedirs(d, exist_ok=True)
    build_wiki(big, os.path.join(d, "wiki.git"))
    build_infra(big, os.path.join(d, "infra"))
    json.dump({"T4": t1_questions(big)}, open(os.path.join(d, "truth.json"), "w"), ensure_ascii=False, indent=2)

    for name in ("small", "big"):
        g = os.path.join(out, name, "wiki.git")
        n = subprocess.run(["git", "-C", g, "ls-tree", "-r", "--name-only", "HEAD"], capture_output=True, text=True).stdout.count(".md\n")
        head = subprocess.run(["git", "-C", g, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        print(f"{name}\tpages={n}\tHEAD={head}")


if __name__ == "__main__":
    main()
