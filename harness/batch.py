#!/usr/bin/env python3
"""Run every task and condition for the given models and repetitions.

    harness/batch.py --models opus,sonnet,haiku --reps 1 [--tasks K1,M1] [--label pilot] [--lanes 3]

Without --tasks, the tasks on real repositories run; the synthetic tasks
(T1-T4) run only when named.

Groups of one model run one after another in a lane; lanes run at the same
time. A group whose directory exists is skipped, so a batch can be resumed.
Progress goes to runs/batch-<label>.log.
"""
import argparse
import datetime
import os
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "harness"))
from run import CONDS, RUNS  # noqa: E402
from real import TASKS  # noqa: E402

ORDER = ["K1", "M1", "K3", "M3", "K5", "W"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--first-rep", type=int, default=1)
    ap.add_argument("--label", default="")
    ap.add_argument("--tasks", default=",".join(ORDER))
    ap.add_argument("--lanes", type=int, default=3)
    a = ap.parse_args()
    models = a.models.split(",")
    runs = RUNS
    os.makedirs(runs, exist_ok=True)
    log = open(os.path.join(runs, f"batch-{a.label or 'main'}.log"), "a")
    lock = threading.Lock()

    def say(msg):
        with lock:
            log.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}\n")
            log.flush()

    jobs = {m: [] for m in models}
    for rep in range(a.first_rep, a.first_rep + a.reps):
        for t in a.tasks.split(","):
            for c in (TASKS[t]["conds"] if t in TASKS else CONDS[t]):
                for m in models:
                    jobs[m].append((t, c, m, rep))
    lanes = [[] for _ in range(a.lanes)]
    for i, m in enumerate(models):
        lanes[i % a.lanes].extend(jobs[m])

    def lane(items):
        for t, c, m, rep in items:
            name = f"{t}-{c}-{m}-r{rep}" + (f"-{a.label}" if a.label else "")
            if os.path.exists(os.path.join(runs, name)):
                say(f"skip {name}")
                continue
            say(f"start {name}")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "harness", "run.py"), "--task", t, "--cond", c,
                                "--model", m, "--rep", str(rep), "--runs", runs] + (["--label", a.label] if a.label else []),
                               capture_output=True, text=True)
            say(f"done {name} rc={r.returncode} {r.stdout.strip()} {r.stderr.strip()[-500:]}")

    threads = [threading.Thread(target=lane, args=(l,)) for l in lanes if l]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    say("batch finished")


if __name__ == "__main__":
    main()
