#!/usr/bin/env python3
"""Make gen/paraphrases.json: descriptions of feature gates reworded in
English ("k8s") and in Japanese ("k8s_ja") so that they share no identifiers
with the page, each checked by a second model call that must pick the right
gate out of ten similar ones.

    gen/paraphrase.py

Runs claude -p in the agent image with the token of harness/eval.py. The
output is committed, since model output cannot be reproduced exactly.
"""
import json
import os
import random
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import real as R  # noqa: E402
import tasks as T  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.environ.get("EVAL_IMAGE", "wikictl-eval-agent:dev")
MODEL = "claude-opus-5"
WANT = 5


def ask(prompt):
    token = open(os.path.expanduser("~/.config/wikictl-eval/oauth-token")).read().strip()
    r = subprocess.run(["docker", "run", "--rm", "-i", "-e", "CLAUDE_CODE_OAUTH_TOKEN", "-e", "CLAUDE_CONFIG_DIR=/tmp/cc",
                        IMAGE, "claude", "-p", "--model", MODEL, "--tools", "", "--output-format", "json"],
                       input=prompt, capture_output=True, text=True, env={**os.environ, "CLAUDE_CODE_OAUTH_TOKEN": token},
                       check=True)
    return json.loads(r.stdout)["result"].strip()


def english(k, name):
    b = T.body(k.docs[k.en[name]["path"]])
    b = re.sub(r"\{\{<[^>]*>\}\}", "", b)
    return " ".join(b.split())


def words(t):
    return set(re.findall(r"[a-z]{4,}", t.lower()))


INSTRUCTIONS = {
    "k8s": "Reword the following description of a Kubernetes feature gate in one or two plain English sentences. "
           "Keep its meaning, but do not use the gate's name, any identifier in CamelCase or with dots, "
           "any backticks, or any phrase of three or more words copied from the description. "
           "Reply with the reworded text only.",
    "k8s_ja": "Explain what the following Kubernetes feature gate does in one or two plain Japanese sentences, as a "
              "colleague would describe it. Keep its meaning, but do not use the gate's name, any identifier in "
              "CamelCase or with dots, any backticks, or any English phrase of two or more words copied from the "
              "description (common single terms such as Pod or kubelet may stay). Reply with the Japanese text only.",
}


def main():
    k = T.K8s()
    path = os.path.join(ROOT, "gen", "paraphrases.json")
    result = json.load(open(path)) if os.path.exists(path) else {"model": MODEL}
    for kind in sys.argv[1:] or INSTRUCTIONS:
        taken = {i["gate"] for key, items in result.items() if key != "model" for i in items}
        result[kind] = generate(k, kind, taken)
        json.dump(result, open(path, "w"), ensure_ascii=False, indent=2)


def generate(k, kind, taken):
    rng = random.Random(f"{T.SEED}:paraphrase:{kind}")
    cands = [n for n, g in k.en.items() if not g["removed"] and 120 <= len(english(k, n)) <= 500 and n not in taken]
    out = []
    for name in rng.sample(sorted(cands), len(cands)):
        desc = english(k, name)
        text = ask(INSTRUCTIONS[kind] + "\n\nDescription:\n" + desc)
        if re.search(r"`|[a-z][A-Z]|\b" + re.escape(name) + r"\b", text):
            continue
        near = sorted((n for n in k.en if n != name), key=lambda n: -len(words(english(k, n)) & words(desc)))[:9]
        options = near + [name]
        rng.shuffle(options)
        listing = "\n".join(f"{i + 1}. {english(k, n)}" for i, n in enumerate(options))
        pick = ask("Which numbered description means the same as the text below? Reply with the number only.\n\n"
                   f"Text: {text}\n\n{listing}")
        if pick.strip().rstrip(".") == str(options.index(name) + 1):
            out.append({"gate": name, "text": text})
            print(name, "|", text, flush=True)
        if len(out) == WANT:
            break
    return out


if __name__ == "__main__":
    main()
