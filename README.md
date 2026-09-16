# wikictl-eval

[日本語](README.ja.md)

Tasks, harness and graders that measure how much [wikictl](https://github.com/roamer7038/wikictl) changes the quality, cost and speed of an agent's work. The purpose and the decisions the results feed are in [roamer7038/wikictl#184](https://github.com/roamer7038/wikictl/issues/184).

## Conditions

| Condition | Documentation repository | Team wiki (K5, W) |
|---|---|---|
| B0 | not available (the model answers from its own knowledge); in K5 only, the clone of B1 | none |
| B1 | a clone, read with `rg`, `cat` and `git` | a clone, written with `git` commit and push |
| B2 | wikictl (one profile per repository) and [wikictl-claude-plugin](https://github.com/roamer7038/wikictl-claude-plugin) | wikictl |

The prompt is the same under every condition except for its environment section ([`tasks/env-real-B0.md`](tasks/env-real-B0.md) and `tasks/src-*.md`).

## Material

Real repositories at pinned commits:

| Repository | Commit | Size |
|---|---|---|
| [kubernetes/website](https://github.com/kubernetes/website) | `aa4e9e6` (2026-09-16) | 8,224 .md files; 487 feature gate pages in English, 466 in the Chinese translation |
| [mdn/content](https://github.com/mdn/content) | `8e307de` (2026-09-16) | 14,661 pages (57 MB) |

The team wiki that K5 and W write to is a small wiki made by [`gen/real.py`](gen/real.py), holding three feature gates already recorded.

## Tasks

The prompts are in Japanese. Every answer is computed by [`gen/real.py`](gen/real.py) from the frontmatter at the pinned commits.

| ID | Task | Conditions | Answers and grading |
|---|---|---|---|
| K1 | Answer 12 questions on feature gates: the stage in v1.37 of 4 gates whose Chinese translation still shows an older stage, the version in which 4 gates entered a stage in v1.36 or v1.37, and the same for 4 stages entered in v1.30 or before | B0 B1 B2 | English `stages`; correct, stale (the translation's value), unknown or wrong |
| M1 | Give the `status` of 12 MDN pages: 5 lost a value in 2026, 4 gained one, 3 did not change in 2026 | B0 B1 B2 | `status`; correct, stale (the value before 2026), unknown or wrong |
| K3 | List every gate matching three conditions such as "entered beta in v1.37" (19, 18 and 18 gates) | B0 B1 B2 | F1 of the sets |
| M3 | List every page matching three conditions such as "CSS properties whose status includes experimental" (60, 9 and 58 pages) | B0 B1 B2 | F1 of the sets |
| K5 | Continue in another session: session 1 lists the gates that entered stable in v1.37 and records what helps the next session; session 2, which keeps neither the conversation nor the working directory, answers three other conditions on v1.36 and v1.37 | B0 B1 B2 | F1 of the sets, cost of session 2, what was written to the wiki |
| W | Three agents at once each look up 5 feature gates, create a page for each and add a row to the same index page | B1 B2 | missing pages and rows, wrong facts, duplicated rows, lost existing rows, row order, `lint` |

Tasks on generated material (T1 to T4, [`gen/build.py`](gen/build.py)) remain, but are not run by default: their answers were easy to find and showed no difference between conditions.

## Measures

- Quality: the grading in the table above; written pages are checked with `lint` of wikictl v0.4.1.
- Cost: USD from the token counts in `modelUsage` of the `result` event of `claude -p`, at the prices in [`grade/prices.json`](grade/prices.json). The intermediate events of `stream-json` under-report output tokens and are not used.
- Speed: wall time, turns and tool calls of a session, and the calls to `wikictl`, `git` and `rg` with the size of their output, logged by wrappers.

## Environment

- Versions: wikictl v0.4.1 (release binary verified against its checksum), plugin b5763e8, Claude Code 2.1.273; the values used are recorded in `build/versions.tsv`.
- Isolation: each session runs through [`harness/jail.sh`](harness/jail.sh) in the namespaces of `unshare -Urmpf`. `/home`, `/tmp` and `/mnt` are empty except for:
  - read-write: the group's directory;
  - read-only: Claude Code, wikictl and the plugin, and, under B1, B2 and the B0 of K5, the pinned documentation repositories.
  - A separate PID namespace keeps `/proc` from reaching the file systems of other processes.
- Configuration: HOME, `CLAUDE_CONFIG_DIR` and PATH are per session, so the user's CLAUDE.md, memory, plugins and MCP servers are not loaded. Only B2 loads the plugin, with `--plugin-dir`. The built-in skills are the same under every condition.
- Tools: Bash, Read, Write, Edit, Glob and Grep (and Skill under B2). Subagents and web tools are not available.
- Preparation: the clone of B1 (`--shared`) and the wikictl mirror of B2 exist before the session starts. The mirror is made once and copied with hard links, so neither condition starts by fetching hundreds of megabytes. The remotes are local repositories, so the time includes no fetch over a network.
- Logs: commands are logged by wrappers on PATH with their parent processes, so that the git that Claude Code runs itself is not counted. Read, Grep and Glob do not pass through the wrappers; they are counted from the transcript as tool calls.

## Reproduce

Requires:
- Linux with unprivileged user namespaces, and `unshare` from util-linux
- Python 3.12 with PyYAML
- git, ripgrep, jq, curl and Claude Code

```sh
./setup.sh                                   # wikictl and the plugin in build/; pinned repositories and questions in data/
claude setup-token                           # save the token it prints to the file below
mkdir -p ~/.config/wikictl-eval && ( umask 077; cat > ~/.config/wikictl-eval/oauth-token )

harness/run.py --task K3 --cond B2 --model sonnet --rep 1           # one group
harness/batch.py --models opus,sonnet,haiku --reps 3                # every task and condition
grade/grade.py ../wikictl-eval-runs/*-r[123] > results/raw/main.jsonl
grade/report.py results/raw/main.jsonl > results/main.md
```

Groups are written to `../wikictl-eval-runs/` (or `$EVAL_RUNS`), outside any Git repository, because Claude Code puts the git status of an enclosing repository into the system prompt. The directory keeps the transcripts, and the environment of the agents holds the authentication token, so do not publish it.

## License

MIT. The material keeps the licenses of its repositories (kubernetes/website: CC-BY-4.0; mdn/content: CC-BY-SA-2.5 for prose, with code examples under their own licenses).
