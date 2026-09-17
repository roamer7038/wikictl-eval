# wikictl-eval

[日本語](README.ja.md)

Tasks, environment and graders that measure how much [wikictl](https://github.com/roamer7038/wikictl) changes the quality, cost and delivery time (QCD) of an agent's work. The purpose and the decisions the results feed are in [roamer7038/wikictl#184](https://github.com/roamer7038/wikictl/issues/184).

- Results: [results/main.md](results/main.md) (main run, 2026-09-17, in Japanese)

## Questions

1. How much do results differ between having the information locally (a clone read with standard commands, or wikictl) and not having it (the model's knowledge only)?
2. What does wikictl (B2), which treats a remote repository as if it were local, need to match or beat a clone with standard commands (B1)?

## Conditions

| Condition | Access to the documentation |
|---|---|
| B0 | none (answers from the model's knowledge); in P8 only, the clone without the team wiki |
| B1 | a clone with `rg`, `cat`, `git` and Claude Code's built-in Read and Grep |
| B2 | wikictl v0.4.1 with [wikictl-claude-plugin](https://github.com/roamer7038/wikictl-claude-plugin) b5763e8 |
| B2-trigger | B2 with the skill description widened so that the skill is loaded for any task through wikictl |
| B2-help | B2 with how to read many files added to the top-level help of wikictl |
| B2-nofetch | B2 with `--no-fetch` added to reads of the documentation |
| B2-skill | a skill with the widened description and how to read many files |
| B2-proto | prototype wikictl (`meta`, `log`, `show`, `snapshot`), the search extension `wikictl-search`, and a skill describing when to use them |
| B2-best | B2-proto with the added help and the fetch before a read skipped for 300 seconds |
| B2-lean | the wikictl and extension of B2-best with a short skill holding only a table of commands (22 lines) |

The prompt is the same under every condition except for its environment section ([`tasks/v2/env-*.md`](tasks/v2/) and `tasks/v2/src-*.md`). The wikictl prototypes are patches to v0.4.1 in [`docker/proto/`](docker/proto/), the skill variants are in [`docker/plugins/`](docker/plugins/), and the search extension is in [`docker/ext/`](docker/ext/).

## Material

Real repositories at pinned commits:

| Repository | Commit | Information used |
|---|---|---|
| [kubernetes/website](https://github.com/kubernetes/website) | `aa4e9e6` | `stages` of the feature gate pages (487 in English, 466 in the Chinese translation), body text and links, history |
| [kubernetes/enhancements](https://github.com/kubernetes/enhancements) | `766deac` | `kep.yaml` of the KEPs (owning-sig, stage, milestone, feature-gates) |
| [mdn/content](https://github.com/mdn/content) | `8e307de` | frontmatter of 14,661 pages (`status`, `page-type`, `slug`), references in the body, history |

The team wiki that P8 and P9 write to is a small wiki made by [`gen/real.py`](gen/real.py).

## Tasks

The prompts are in Japanese. [`gen/tasks.py`](gen/tasks.py) computes the answers from the pinned commits (`data/tasks/truth.json`).

| ID | Kind | Content | Grading |
|---|---|---|---|
| L1 | values | 14 questions on feature gates (the stage in v1.37 of gates whose Chinese translation is out of date, versions of recent and old stages, gates that do not exist) | correct, stale, unknown, wrong |
| L2 | values | `status` of 14 MDN pages (lost or gained a value in 2026, unchanged, pages that do not exist) | as L1 |
| P2 | full-text search | the only page under `content/en/docs` that mentions a flag (8 questions) | correct |
| P3K, P3M | aggregation | gates (19, 18 and 18) and MDN pages (60, 9 and 58) matching conditions | F1 |
| P4 | history | the date a stable stage was added to a gate page, and the date experimental was removed from an MDN page (8 questions) | correct (author, commit or merge date) |
| P5 | vague descriptions | identify gates from Japanese descriptions (5) and English rewordings (5) without their names; the texts were written by Opus and kept only when a second call identified the gate ([`gen/paraphrase.py`](gen/paraphrase.py)) | correct |
| P6 | several hops | the title of the page a gate page links to first, other KEPs of the SIG of the KEP that introduced a gate, the status of the API an MDN page refers to first (9 questions) | correct, F1 |
| P7 | two repositories | gates whose stable version differs between KEP and documentation, and gates stable in the KEP with no stable stage in the documentation | F1 |
| P8 | continue in another session | team decisions given only in the first session's prompt, used with the documentation in a second session that keeps neither the conversation nor the working directory | F1 of session 2 |
| P9 | writing at the same time | three agents each look up 5 gates, create a page for each and add rows to the same index | missing, wrong facts, duplicated, lost existing rows, order |

A success is every question correct (F1 ≥ 0.95 counting as correct) without breaking the rules of the prompt. Rule breaks, such as reading the wikictl mirror with git or reaching the remote with git directly under B2, are counted by [`grade/score.py`](grade/score.py).

## Measures

- Quality (Q): the score (mean over questions of 1/0 or F1) and success.
- Cost (C): USD from the token counts in `modelUsage` of the `result` event of `claude -p`, at the prices in [`grade/prices.json`](grade/prices.json).
- Delivery (D): wall time of a session; for P9 the longest of the three agents.
- Diagnostics: tool calls with their time and output size from the transcript, runs of `wikictl`, `git` and `rg` logged by wrappers, skill loading, use of the prototype commands, rule breaks.

## Environment

- Docker: one container (2 CPUs, 6 GB) per session. The image ([`docker/agent.Dockerfile`](docker/agent.Dockerfile)) holds Claude Code 2.1.273, wikictl v0.4.1 (release binary verified against its checksum) and the prototypes, the plugin variants, and `wikictl-search` with a multilingual embedding model (paraphrase-multilingual-MiniLM-L12-v2).
- Remote: git daemon containers serve the pinned repositories and the team wiki, one without delay (`git0`) and one adding 40 ms to each packet it sends (`git40`).
- Preparation: the B1 clones, the wikictl mirrors of the B2 conditions and the `wikictl-search` index are made once and copied into each session, so no condition starts by fetching hundreds of megabytes.
- Isolation: a session sees only its HOME, working directory and documentation clones; the user's CLAUDE.md, memory, plugins and MCP servers are not loaded. Tools: Bash, Read, Write, Edit, Glob and Grep (and Skill under B2 conditions).
- Usage limits: a group whose session ended on a usage limit is moved aside and run again after the reset time given in the message.

## Reproduce

Requires Linux, Docker, Python 3.12 with PyYAML, git, curl and Claude Code (to make the token).

```sh
./setup.sh                          # pinned repositories (data/remotes) and generated material
python3 gen/real.py && python3 gen/tasks.py   # questions and answers (data/tasks)
docker build -t wikictl-eval-agent:v4 -f docker/agent.Dockerfile docker
docker build -t wikictl-eval-gitserver:dev -f docker/gitserver.Dockerfile docker
claude setup-token                  # save the token it prints to the file below
mkdir -p ~/.config/wikictl-eval && ( umask 077; cat > ~/.config/wikictl-eval/oauth-token )

export EVAL_IMAGE=wikictl-eval-agent:v4
harness/eval.py run --task P3K --cond B2-lean --model sonnet --rep 1          # one group
harness/eval.py batch --tasks L1,L2,P2,P3K,P3M,P4,P5,P6,P7,P8,P9 \
  --conds B0,B1,B2,B2-best,B2-lean --models opus,sonnet,haiku --reps 3 --label main
grade/score.py ../wikictl-eval-runs/*-main > results/main-scores.jsonl
grade/qcd.py results/main-scores.jsonl > results/main-qcd.md
```

Groups are written to `../wikictl-eval-runs/` (or `$EVAL_RUNS`), outside any Git repository, because Claude Code puts the git status of an enclosing repository into the system prompt. The directory keeps the transcripts, and the agent containers receive the authentication token, so do not publish it.

The earlier environment (generated material T1 to T4, and K1, M1, K3, M3, K5 and W on kubernetes and mdn isolated with unshare) remains in `harness/run.py`, `harness/real.py` and `harness/jail.sh`.

## License

MIT. The material keeps the licenses of its repositories (kubernetes/website: CC-BY-4.0; kubernetes/enhancements: Apache-2.0; mdn/content: CC-BY-SA-2.5 for prose).
