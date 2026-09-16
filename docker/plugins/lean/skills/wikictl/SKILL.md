---
name: wikictl
description: Search, read and record files in Markdown repositories with the wikictl CLI, including documentation repositories set up as wikictl profiles. Use before the first wikictl command of a task and whenever a task reads, searches, counts or writes files through wikictl; also before answering with values specific to a machine, project or user, when a command fails, and when work produces a reusable fact worth recording.
allowed-tools: Bash
---

# wikictl

`wikictl` reads and writes a Markdown repository with git alone. Commands work like the Linux commands of the same name and take paths from the repository root; `--profile <name>` picks the repository, `--json` gives machine-readable output, and `wikictl help <command>` has the details.

Read in as few commands as possible; every command is a process that talks to the remote:

| Need | Command |
|---|---|
| Find files that mention words | `wikictl grep -l -e <word> <dir>`; `-n` for lines, `-c` for counts |
| Read files | `wikictl cat <path>...` with all paths in one call; `--json` for `jq` |
| Frontmatter of many pages | `wikictl meta [--keys k1,k2] <dir>` |
| History of a file | `wikictl log [-p] <path>`, then `wikictl show <commit> <path>` |
| Scan many files with rg, Read or Grep | `wikictl snapshot <local-dir> <dir>`, then read the copy |
| Pages matching a vague or translated description | `wikictl-search [--profile P] "<description>" [<dir>]` |

Write a page with `wikictl put --json <path> < page.md`; to change one, take `sha` from `wikictl cat --json <path>` and pass `--base <sha>`. Exit code 3 is a conflict: read the file again, reapply the change and put again.
