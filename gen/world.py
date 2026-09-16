"""The facts of the generated organisation, from which the wiki, the
workspace and the answers are all derived.

A world is plain data: projects with services, machines, people and a
history of changed values. The same seed gives the same world; a larger
scale keeps the core entities of the small world unchanged and appends
filler entities after them.
"""
import random

CORE_PROJECTS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]
CORE_MACHINES = ["kiso", "hayate", "tsubame", "mogami", "asuka", "hibiki", "raicho", "shirane", "kurobe", "nagara"]
PEOPLE = [
    ("aoki", "platform"), ("baba", "data"), ("chiba", "web"), ("doi", "platform"),
    ("endo", "data"), ("fujii", "web"), ("goto", "security"), ("hara", "security"),
]
ROLES = ["api", "web", "worker", "batch", "gateway", "auth", "search", "notify"]
QUEUES = ["nats", "rabbitmq", "kafka", "redis-streams"]
QUEUE_REASONS = {
    "nats": "運用するプロセスが 1 つで済む",
    "rabbitmq": "遅延キューが標準で使える",
    "kafka": "再処理のためにイベントを 30 日保持できる",
    "redis-streams": "既存の Redis をそのまま使える",
}
OS_VERSIONS = ["Ubuntu 22.04.5", "Ubuntu 24.04.2", "Ubuntu 24.04.3", "Debian 12.11", "Rocky Linux 9.6"]
DRIVERS = ["535.247.01", "550.163.01", "570.124.06", "570.172.08", "580.65.06"]
PG_VERSIONS = ["15.13", "16.9", "16.10", "17.5", "17.6"]
BASE_DATE = "2026-03-02"

# Base kinds of the deploy repository used by T2: defaults per kind, and the
# kind each one extends.
DEPLOY_KINDS = {
    "common": {"extends": None, "values": {"replicas": 1, "memory": "256Mi", "port": 8080}},
    "http": {"extends": "common", "values": {"replicas": 2, "memory": "512Mi"}},
    "job": {"extends": "common", "values": {"memory": "1Gi", "port": 9100}},
    "edge": {"extends": "http", "values": {"replicas": 3, "port": 8443}},
}
ROLE_KIND = {"api": "http", "web": "http", "worker": "job", "batch": "job",
             "gateway": "edge", "auth": "http", "search": "http", "notify": "job"}
MEMORY = ["256Mi", "512Mi", "768Mi", "1Gi", "2Gi"]


def _filler_names(rng, prefix, n, taken):
    words = ["amber", "birch", "cedar", "dune", "ember", "fjord", "grove", "heath", "iris", "jade",
             "kelp", "larch", "moss", "nectar", "onyx", "pine", "quartz", "reed", "sage", "tide"]
    out = []
    i = 0
    while len(out) < n:
        name = f"{prefix}{words[i % len(words)]}-{i // len(words) + 1}"
        i += 1
        if name not in taken:
            out.append(name)
    return out


def _date(day_offset):
    y, m, d = map(int, BASE_DATE.split("-"))
    import datetime
    return (datetime.date(y, m, d) + datetime.timedelta(days=day_offset)).isoformat()


def make_world(seed=184, projects=8, machines=10):
    rng = random.Random(seed)
    project_names = CORE_PROJECTS[:projects] + _filler_names(rng, "", max(0, projects - len(CORE_PROJECTS)), set(CORE_PROJECTS))
    machine_names = CORE_MACHINES[:machines] + _filler_names(rng, "host-", max(0, machines - len(CORE_MACHINES)), set(CORE_MACHINES))

    # Each entity draws from its own generator so that appending filler
    # entities does not change the core ones.
    def sub(key):
        return random.Random(f"{seed}:{key}")

    world = {"seed": seed, "people": [{"name": n, "team": t} for n, t in PEOPLE],
             "machines": [], "projects": [], "changes": []}
    ports_used = set()
    for h in machine_names:
        r = sub(f"machine:{h}")
        m = {
            "name": h,
            "os": r.choice(OS_VERSIONS),
            "driver": r.choice(DRIVERS),
            "backup": r.choice([f"/mnt/nas{r.randint(1, 3)}/backup/{h}", f"s3://bk-{h}-{r.randint(100, 999)}"]),
            "ssh_port": r.choice([22, 2222, 10022, 20022]),
        }
        world["machines"].append(m)
    for p in project_names:
        r = sub(f"project:{p}")
        roles = r.sample(ROLES, 3)
        proj = {"name": p, "queue": r.choice(QUEUES), "lead": r.choice(PEOPLE)[0], "services": [],
                "env_prod": _deploy_layer(r, 0.5)}
        for role in roles:
            port = r.randrange(3000, 9000, 10)
            while port in ports_used:
                port += 7
            ports_used.add(port)
            s = {
                "name": f"{p}-{role}",
                "role": role,
                # Core services run on core machines and filler services on
                # filler machines, so that filler changes leave core ones alone.
                "host": machine_names[r.randrange(min(len(machine_names), len(CORE_MACHINES)))]
                if p in CORE_PROJECTS else r.choice(machine_names[len(CORE_MACHINES):] or machine_names),
                "port": port,
                "postgres": r.choice(PG_VERSIONS),
                "owner": r.choice(PEOPLE)[0],
                "deploy": f"make deploy SERVICE={p}-{role} ENV=prod" if r.random() < 0.5
                else f"./scripts/release.sh {p}-{role} --env prod",
            }
            s["deploy_overrides"] = _deploy_overrides(r, role)
            proj["services"].append(s)
        world["projects"].append(proj)

    # Changed values: the old value was current first and is still mentioned
    # in a meeting note; the canonical page was updated later.
    for i, p in enumerate(world["projects"]):
        r = sub(f"changes:{p['name']}")
        day = 20 + i % 30
        cands = [("machine", mm["name"], k) for mm in world["machines"] for k in ("driver", "backup")
                 if any(s["host"] == mm["name"] for s in p["services"])]
        cands += [("service", s["name"], k) for s in p["services"] for k in ("port", "owner", "postgres")]
        cands += [("project", p["name"], "queue")]
        for kind, name, key in r.sample(cands, 2):
            if any(c["kind"] == kind and c["name"] == name and c["key"] == key for c in world["changes"]):
                continue
            ent = find(world, kind, name)
            new = ent[key]
            old = _other_value(r, key, new, name)
            world["changes"].append({"kind": kind, "name": name, "key": key, "old": old, "new": new,
                                     "project": p["name"], "note_date": _date(day),
                                     "updated": _date(day + 40 + r.randint(0, 20))})
    return world


def _deploy_overrides(r, role):
    """Values a service sets in the deploy repository: in its own file and in
    the prod environment."""
    return {"service": _deploy_layer(r, 0.6), "env_service": _deploy_layer(r, 0.35)}


def _deploy_layer(r, prob):
    vals = {}
    if r.random() < prob:
        key = r.choice(["replicas", "memory", "port"])
        vals[key] = {"replicas": r.randint(1, 6), "memory": r.choice(MEMORY),
                     "port": r.choice([8000, 8081, 8443, 9000, 9090, 9100])}[key]
    return vals


def _other_value(r, key, new, name):
    pools = {"driver": DRIVERS, "postgres": PG_VERSIONS, "queue": QUEUES,
             "owner": [n for n, _ in PEOPLE]}
    if key in pools:
        return r.choice([v for v in pools[key] if v != new])
    if key == "port":
        return new + r.choice([1, 10, 100])
    if key == "backup":
        return f"/srv/backup/{name}" if not new.startswith("/srv") else f"/mnt/old/{name}"
    raise ValueError(key)


def find(world, kind, name):
    if kind == "machine":
        return next(m for m in world["machines"] if m["name"] == name)
    if kind == "project":
        return next(p for p in world["projects"] if p["name"] == name)
    return next(s for p in world["projects"] for s in p["services"] if s["name"] == name)


def project_of(world, service):
    return next(p for p in world["projects"] if any(s["name"] == service for s in p["services"]))


def old_value(world, kind, name, key):
    for c in world["changes"]:
        if (c["kind"], c["name"], c["key"]) == (kind, name, key):
            return c["old"]
    return None


def updated_of(world, kind, name):
    dates = [c["updated"] for c in world["changes"] if c["kind"] == kind and c["name"] == name]
    return max(dates, default=BASE_DATE)


def effective_deploy(world, service_name):
    """Effective prod values of a service in the deploy repository (T2)."""
    s = find(world, "service", service_name)
    chain = []
    k = ROLE_KIND[s["role"]]
    while k:
        chain.append(k)
        k = DEPLOY_KINDS[k]["extends"]
    vals = {}
    for k in reversed(chain):
        vals.update(DEPLOY_KINDS[k]["values"])
    vals.update(s["deploy_overrides"]["service"])
    vals.update(project_of(world, service_name)["env_prod"])
    vals.update(s["deploy_overrides"]["env_service"])
    return vals
