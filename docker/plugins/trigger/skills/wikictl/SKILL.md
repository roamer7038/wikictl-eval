---
name: wikictl
description: Search, read and record files in Markdown repositories with the wikictl CLI, including documentation repositories set up as wikictl profiles. Use before the first wikictl command of a task and whenever a task reads, searches, counts or writes files through wikictl; also before answering with values specific to a machine, project or user, when a command fails, and when work produces a reusable fact worth recording.
allowed-tools: Bash
---

# wikictl

The wiki is a Markdown repository on a Git host; `wikictl` (v0.4.1 or later) reads and writes it with git alone. Its commands behave like the Linux commands of the same name (`grep`, `cat`, `stat`, `ls`, `find`, `tree`, `mv`, `rm`), take paths from the wiki root, and accept flags before or after the arguments. Add `--json` for machine-readable output. `wikictl help <command>` describes any command.

## When

- Read before answering with environment-specific values, the user's conventions, past decisions, or rules.
- Read when a command or procedure fails: a workaround may be recorded.
- Read before writing: a page for the same question may exist.
- Write when work yields a reusable fact: a failure and its workaround, an environment-specific value, a decision and its reason.
- Do not write conversation summaries or repeatable procedures (skills). A rule that must hold in every conversation without searching is a standing instruction: suggest adding it to CLAUDE.md instead. In a wiki used by one person, a user fact looked up only when relevant (which account to use, tool choices) goes in `personal/`.

## Choose the paths

wikictl never picks directories from the current directory: a command without paths covers the whole wiki. Narrow a search with the scope directories that apply:

1. `wikictl tree -d -L 2` shows the directories.
2. Choose the `projects/<name>` of the current project and the `machines/<name>` of this machine. The recommended names are the last element of `git remote get-url origin` without `.git`, and `hostname` up to the first `.`, both lowercase; the directory in the tree may differ.
3. Search `global`, `personal`, and those directories. Pass only directories that exist: `grep` reports a missing one and exits with 2.

## Read

```bash
set -o pipefail   # the pipeline exits with grep's code, not 0
wikictl grep -il --all-match -e <word> -e <word> global personal projects/<name> machines/<name> \
  | tr '\n' '\0' | xargs -0 -r wikictl ls -lt   # matching files with type, last update and summary, newest first
wikictl cat <path>...             # files as stored
wikictl stat <path>...            # sha, updated, title, summary, type, tags, status, aliases
wikictl links <path>              # links in the page (out) and to it (in), with their type
wikictl find <path>... -meta type=decision   # also -name '*lease*', -type d, -mtime -7
```

`grep` works like `grep -r`:

- Patterns are case-sensitive basic regular expressions: add `-i`, and `-F` for a term with `.`, `*` or `[`. `-i` ignores the case of letters other than ASCII (`École`) only together with `-F`.
- Give each term its own `-e`; `--all-match` keeps the files that contain every term. A quoted `"local LLM"` matches only that exact spacing.
- A term also matches inside longer words (`go` in `goenv`); add `-w` for short words.

Choose what to read from `summary` in `ls -lt`, not from position; add a term when the list is long. `tr '\n' '\0' | xargs -0` passes names with quotes or spaces intact (a name with a newline is not supported), and `-r` runs nothing when `grep` finds nothing. Read the exit code of the pipeline as `grep`'s (see Exit codes): without `pipefail` it is 0 even when `grep` failed.

No match, or no `summary` that answers the question, does not yet mean the wiki lacks the answer. Retry in this order, stopping when a `summary` answers the question:

1. Fewer words, a synonym, or the term in the other language of the wiki (`リランカー` / `reranker`).
2. The same queries without paths: knowledge about a tool or another project may live elsewhere in the wiki.

Only when these also fail, find the answer elsewhere and consider recording it. If `stat` shows an old `updated` or `links` shows a `contradicts` link, say so instead of presenting the value as settled.

## Write

1. `grep` for a page answering the same question.
2. New page: `wikictl put --json <path> < page.md`. Missing directories are created. Without `--json` or `-v`, `put` prints nothing on success.
3. Existing page: `wikictl cat --json <path>` prints `content` and `sha`. Write `content` to a temporary file, edit it, then `wikictl put --json --base <sha> <path> < page.md`. The `sha` printed by `put --json` is valid for the next `--base`.

A page is frontmatter, a title, the body, and, when it has links, a `## Links` section as the last heading; add body text above it, since lines after the links are reported as `links_syntax`. Always write a one-line `summary`: `ls -l` shows it. `type` is optional (concept, procedure, decision, policy, observation, event, index, source). Write links to pages as `[text](path)`, a path relative to the page: `mv` rewrites only that form. Name files and directories with lowercase letters, digits and hyphens.

```markdown
---
summary: Go on laptop is 1.26.5, installed with goenv under ~/.anyenv
type: observation
---
# Which Go is installed on laptop?

`go version` prints go1.26.5; goenv manages it.

## Links
- cites: https://go.dev/dl/ | release list
```

`put` prints warnings (missing summary, broken link, Links syntax, name style) on standard error and still writes the page. Fix them; `wikictl lint <path>` checks again.

## Placement

wikictl gives no meaning to directory names; the layout below is this plugin's convention. Choose the narrowest scope that fits:

| Directory | Knowledge valid |
|---|---|
| `projects/<name>/` | in one project |
| `machines/<name>/` | in one execution environment |
| `personal/` | only for this user, on every machine and in every project; not used in a wiki shared by several people |
| `global/` | for everyone |

Before creating a directory, run `wikictl tree -d` and reuse an existing one when it fits.

- Rename or move a page or directory with `wikictl mv -T <src> <dst>`; without `-T`, a `<dst>` that is an existing directory receives `<src>` inside it. `mv` rewrites `[text](path)` links, adds the old name to `aliases`, and never replaces an existing file or directory (exit code 1, `not replacing`). A `.md` file that is not a page, such as one under a directory whose name starts with a dot, moves with its content unchanged, and links to it are rewritten too.
- Delete with `wikictl rm <path>...`, and a directory with `rm -r` (without it, exit code 1). `rm` does not apply the file name rules, so a file added by a person, such as one whose name holds a space, can be deleted. Links to deleted pages are left as they are; `lint` reports them as `broken_link`.

Never write secrets; write the secret's name instead. Cite sources by URL.

## Exit codes

| Code | Meaning | Action |
|---|---|---|
| 1 | error, such as a path that does not exist or a refused `mv` or `rm` (see Placement); from `grep`: nothing matched | Show the message; for `grep`, retry as in Read |
| 2 | usage error, not configured, or a configuration error such as an unknown profile; from `grep`: a path does not exist, while the other paths are still searched | Show the message; run `/wikictl:setup` when no config exists |
| 3 | conflict; `reason` in the output says which | `exists` from `put`: the file exists, so `cat --json` it and update with `--base`, or choose another path. `changed`: if `content` lacks the change, reapply it and `put` again with `--base <sha>`; if it already has it, stop. Empty `sha` and `content`: the page was deleted since it was read; ask before recreating it. From `mv` or `rm`: nothing was written; re-read the page and run the command again. `moved`: another push won the race, so nothing was written and there is no `content` or `sha`; run the same command again |
| 4 | `put`, `edit` or `mv`: invalid frontmatter, a page over the size limits, a bad path such as a name with whitespace or a file at the wiki root (rules in `wikictl help lint`), or a path git refuses to store, reported as `bad_path: <path>: git refuses the path` (a component such as `git~1`, which names `.git` on NTFS); `rm`: a file at the wiki root; `lint`: any finding | Fix and retry |
| 5 | git failure while reading or writing, such as a push that retrying cannot fix (no permission, a stale lock file, a hook rejection); no partial result is printed | Report the message; do not retry blindly, and do not treat a failed `grep` as no match |

Text output shows control characters as `\xNN`; `--json` has the stored value.
