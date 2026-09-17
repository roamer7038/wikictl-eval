# QCD

Q: score 0–1 (success rate), C: USD, D: minutes. Mean over n repetitions.

## Delay 40 ms

### Overall (tasks each condition ran)

| model | cond | tasks | mean score | success rate | total USD | total min | USD per success |
|---|---|---|---|---|---|---|---|
| opus | B0 | 3 | 0.26 | 0.00 | 0.78 | 3.5 | - |
| opus | B1 | 11 | 1.00 | 1.00 | 5.16 | 15.3 | 0.47 |
| opus | B2 | 11 | 0.99 | 0.91 | 9.27 | 27.5 | 0.93 |
| opus | B2-best | 11 | 1.00 | 1.00 | 7.45 | 17.4 | 0.68 |
| opus | B2-lean | 11 | 1.00 | 1.00 | 5.51 | 15.9 | 0.50 |
| sonnet | B0 | 3 | 0.23 | 0.00 | 0.56 | 5.2 | - |
| sonnet | B1 | 11 | 1.00 | 1.00 | 2.89 | 14.7 | 0.26 |
| sonnet | B2 | 11 | 0.99 | 0.91 | 4.52 | 25.4 | 0.45 |
| sonnet | B2-best | 11 | 1.00 | 1.00 | 4.11 | 18.3 | 0.37 |
| sonnet | B2-lean | 11 | 1.00 | 0.97 | 3.47 | 18.3 | 0.33 |
| haiku | B0 | 3 | 0.31 | 0.22 | 0.52 | 7.4 | 0.79 |
| haiku | B1 | 11 | 0.86 | 0.73 | 1.89 | 17.7 | 0.24 |
| haiku | B2 | 11 | 0.89 | 0.67 | 2.25 | 40.8 | 0.31 |
| haiku | B2-best | 11 | 0.90 | 0.79 | 2.14 | 21.2 | 0.25 |
| haiku | B2-lean | 11 | 0.84 | 0.58 | 2.20 | 24.3 | 0.35 |

### L1

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B0 | 3 | 0.43 | 0.00 | 0.224 | 1.2 | 3 | 0 | 0 | - |
| opus | B1 | 3 | 1.00 | 1.00 | 0.240 | 0.9 | 10 | 0 | 0 | rg 2×/1s, git status 0×/0s, git log 1×/0s |
| opus | B2 | 3 | 1.00 | 1.00 | 0.356 | 1.2 | 10 | 0 | 0 | wikictl cat 19×/8s, wikictl ls 3×/4s, wikictl grep 4×/2s |
| opus | B2-best | 3 | 1.00 | 1.00 | 0.356 | 1.0 | 9 | 0 | 0 | wikictl ls 1×/1s, wikictl grep 3×/1s, wikictl find 1×/0s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.243 | 0.9 | 9 | 0 | 0 | wikictl ls 1×/2s, wikictl grep 2×/0s, wikictl snapshot 1×/0s |
| sonnet | B0 | 3 | 0.29 | 0.00 | 0.189 | 2.1 | 2 | 0 | 0 | - |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.122 | 0.5 | 15 | 0 | 0 | git log 2×/0s, rg 1×/0s |
| sonnet | B2 | 3 | 1.00 | 1.00 | 0.148 | 0.8 | 11 | 0 | 0 | wikictl cat 13×/5s, wikictl ls 3×/4s, wikictl grep 4×/3s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.171 | 0.7 | 11 | 0 | 0 | wikictl grep 7×/1s, wikictl find 9×/1s, wikictl cat 10×/1s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.109 | 0.9 | 10 | 0 | 0 | wikictl ls 3×/3s, wikictl grep 6×/1s, wikictl cat 6×/1s |
| haiku | B0 | 3 | 0.36 | 0.33 | 0.101 | 2.2 | 19 | 0 | 0 | git clone 0×/10s |
| haiku | B1 | 3 | 1.00 | 1.00 | 0.122 | 1.2 | 28 | 0 | 0 | git log 1×/0s |
| haiku | B2 | 3 | 1.00 | 1.00 | 0.203 | 1.7 | 35 | 0 | 0 | wikictl ls 4×/6s, wikictl cat 15×/6s, wikictl grep 7×/3s |
| haiku | B2-best | 3 | 1.00 | 1.00 | 0.131 | 1.3 | 26 | 0 | 0 | wikictl ls 4×/4s, wikictl grep 5×/2s, wikictl cat 13×/1s |
| haiku | B2-lean | 3 | 1.00 | 1.00 | 0.119 | 1.2 | 25 | 0 | 0 | wikictl grep 6×/2s, wikictl find 13×/1s, wikictl cat 11×/1s |

### L2

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B0 | 3 | 0.36 | 0.00 | 0.194 | 0.9 | 3 | 0 | 0 | - |
| opus | B1 | 3 | 1.00 | 1.00 | 0.156 | 0.5 | 6 | 0 | 0 | rg 2×/0s, git log 2×/0s |
| opus | B2 | 3 | 1.00 | 1.00 | 0.363 | 1.1 | 10 | 0 | 0 | wikictl cat 15×/7s, wikictl stat 6×/3s, wikictl ls 1×/1s |
| opus | B2-best | 3 | 1.00 | 1.00 | 0.361 | 1.0 | 10 | 0 | 0 | wikictl stat 6×/2s, wikictl grep 2×/1s, wikictl log 9×/1s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.206 | 0.7 | 7 | 0 | 0 | wikictl ls 1×/1s, wikictl cat 2×/0s, wikictl grep 0×/0s |
| sonnet | B0 | 3 | 0.40 | 0.00 | 0.121 | 1.2 | 3 | 0 | 0 | - |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.085 | 0.5 | 6 | 0 | 0 | git log 1×/0s |
| sonnet | B2 | 3 | 1.00 | 1.00 | 0.103 | 0.7 | 7 | 0 | 0 | wikictl cat 15×/6s, wikictl grep 2×/1s, wikictl ls 1×/1s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.146 | 0.7 | 8 | 0 | 0 | wikictl stat 5×/2s, wikictl cat 14×/1s, wikictl tree 1×/1s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.129 | 0.8 | 10 | 0 | 0 | wikictl ls 1×/1s, wikictl cat 2×/0s, wikictl grep 2×/0s |
| haiku | B0 | 3 | 0.57 | 0.33 | 0.150 | 2.2 | 31 | 0 | 0 | git core.quotePath=false 210×/26s, git remote 29×/0s |
| haiku | B1 | 3 | 1.00 | 1.00 | 0.118 | 1.4 | 24 | 0 | 0 | - |
| haiku | B2 | 3 | 0.98 | 0.67 | 0.137 | 1.6 | 28 | 0 | 0 | wikictl cat 28×/12s, wikictl ls 8×/9s, wikictl find 1×/0s |
| haiku | B2-best | 3 | 1.00 | 1.00 | 0.112 | 1.1 | 20 | 0 | 0 | wikictl cat 17×/2s, wikictl tree 1×/1s, wikictl grep 2×/1s |
| haiku | B2-lean | 3 | 1.00 | 1.00 | 0.131 | 1.3 | 26 | 0 | 0 | wikictl ls 3×/3s, wikictl grep 5×/2s, wikictl cat 14×/2s |

### P2

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B1 | 3 | 1.00 | 1.00 | 0.105 | 0.4 | 6 | 0 | 0 | git log 1×/0s, rg 9×/0s |
| opus | B2 | 3 | 1.00 | 1.00 | 0.210 | 0.7 | 6 | 0 | 0 | wikictl grep 11×/5s, wikictl tree 1×/1s, wikictl help 1×/0s |
| opus | B2-best | 3 | 1.00 | 1.00 | 0.179 | 0.4 | 4 | 0 | 0 | wikictl grep 8×/1s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.121 | 0.5 | 5 | 0 | 0 | wikictl snapshot 1×/0s, wikictl grep 1×/0s, rg 5×/0s |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.035 | 0.2 | 3 | 0 | 0 | git status 0×/0s, git log 1×/0s, rg 8×/0s |
| sonnet | B2 | 3 | 1.00 | 1.00 | 0.070 | 0.4 | 5 | 0 | 0 | wikictl grep 11×/8s, wikictl context 0×/0s, wikictl help 2×/0s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.097 | 0.5 | 9 | 0 | 0 | wikictl grep 14×/2s, wikictl cat 0×/0s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.055 | 0.4 | 11 | 0 | 0 | wikictl grep 9×/1s |
| haiku | B1 | 3 | 1.00 | 1.00 | 0.054 | 0.7 | 11 | 0 | 0 | rg 10×/0s |
| haiku | B2 | 3 | 1.00 | 1.00 | 0.070 | 0.9 | 16 | 0 | 0 | wikictl grep 15×/6s, wikictl ls 0×/0s, wikictl cat 1×/0s |
| haiku | B2-best | 3 | 1.00 | 1.00 | 0.062 | 0.7 | 12 | 0 | 0 | wikictl grep 9×/1s, wikictl search 0×/0s, wikictl help 1×/0s |
| haiku | B2-lean | 3 | 1.00 | 1.00 | 0.062 | 0.9 | 15 | 0 | 0 | wikictl grep 15×/6s, wikictl cat 1×/0s, wikictl help 1×/0s |

### P3K

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B1 | 3 | 1.00 | 1.00 | 0.503 | 1.8 | 18 | 0 | 0 | git log 1×/0s, rg 2×/0s |
| opus | B2 | 3 | 1.00 | 1.00 | 0.685 | 2.4 | 19 | 0 | 0 | wikictl ls 4×/6s, wikictl cat 5×/2s, wikictl find 3×/1s |
| opus | B2-best | 3 | 1.00 | 1.00 | 0.516 | 1.6 | 14 | 0 | 0 | wikictl find 1×/0s, wikictl ls 0×/0s, wikictl snapshot 1×/0s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.472 | 1.7 | 14 | 0 | 0 | wikictl ls 1×/2s, wikictl log 1×/0s, wikictl snapshot 2×/0s |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.206 | 1.1 | 15 | 0 | 0 | git status 0×/0s, git log 2×/0s, rg 3×/0s |
| sonnet | B2 | 3 | 1.00 | 1.00 | 0.340 | 2.1 | 23 | 0 | 0 | wikictl cat 8×/3s, wikictl find 4×/1s, wikictl tree 1×/1s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.202 | 1.1 | 15 | 0 | 0 | wikictl tree 1×/2s, wikictl find 4×/1s, wikictl cat 3×/0s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.303 | 1.9 | 25 | 0 | 0 | wikictl log 2×/1s, wikictl ls 1×/1s, wikictl find 4×/0s |
| haiku | B1 | 3 | 1.00 | 1.00 | 0.094 | 1.1 | 19 | 0 | 0 | git log 1×/0s |
| haiku | B2 | 3 | 1.00 | 1.00 | 0.178 | 9.0 | 24 | 0 | 0 | wikictl cat 1287×/546s, wikictl ls 4×/6s, wikictl find 3×/1s |
| haiku | B2-best | 3 | 0.99 | 0.67 | 0.165 | 1.6 | 25 | 0 | 0 | wikictl ls 1×/2s, wikictl find 6×/1s, wikictl cat 5×/0s |
| haiku | B2-lean | 3 | 0.88 | 0.33 | 0.114 | 1.3 | 19 | 0 | 0 | wikictl cat 169×/18s, wikictl grep 2×/1s, wikictl ls 1×/1s |

### P3M

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B1 | 3 | 1.00 | 1.00 | 0.246 | 1.6 | 10 | 0 | 0 | rg 2×/0s, git log 1×/0s |
| opus | B2 | 3 | 1.00 | 1.00 | 0.509 | 1.8 | 19 | 0 | 0 | wikictl find 8×/21s, wikictl grep 6×/4s, wikictl cat 6×/2s |
| opus | B2-best | 3 | 1.00 | 1.00 | 0.350 | 0.9 | 12 | 0 | 0 | wikictl meta 2×/2s, wikictl tree 1×/2s, wikictl cat 1×/0s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.288 | 1.1 | 11 | 0 | 0 | wikictl ls 2×/3s, wikictl find 2×/3s, wikictl meta 1×/2s |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.143 | 1.0 | 12 | 0 | 0 | git status 1×/0s, git log 2×/0s |
| sonnet | B2 | 3 | 1.00 | 1.00 | 0.214 | 1.4 | 14 | 0 | 0 | wikictl cat 44×/20s, wikictl find 8×/14s, wikictl grep 6×/2s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.166 | 0.9 | 11 | 0 | 0 | wikictl meta 5×/4s, wikictl tree 1×/1s, wikictl find 2×/0s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.183 | 1.0 | 18 | 0 | 0 | wikictl ls 3×/3s, wikictl meta 5×/2s, wikictl grep 0×/0s |
| haiku | B1 | 3 | 1.00 | 1.00 | 0.089 | 1.2 | 16 | 0 | 0 | git log 0×/0s |
| haiku | B2 | 3 | 1.00 | 1.00 | 0.150 | 5.0 | 23 | 0 | 0 | wikictl cat 588×/251s, wikictl find 9×/13s, wikictl grep 2×/3s |
| haiku | B2-best | 3 | 0.99 | 1.00 | 0.140 | 1.6 | 22 | 0 | 0 | wikictl tree 2×/3s, wikictl ls 4×/3s, wikictl meta 7×/2s |
| haiku | B2-lean | 3 | 1.00 | 1.00 | 0.117 | 1.7 | 23 | 0 | 0 | wikictl find 9×/8s, wikictl cat 65×/6s, wikictl ls 5×/5s |

### P4

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B1 | 3 | 1.00 | 1.00 | 0.294 | 1.1 | 12 | 0 | 0 | git log 10×/7s, git show 5×/0s, git branch 0×/0s |
| opus | B2 | 3 | 0.88 | 0.00 | 1.605 | 6.6 | 33 | 0 | 3 | wikictl find 17×/35s, wikictl stat 67×/29s, wikictl cat 36×/14s |
| opus | B2-best | 3 | 1.00 | 1.00 | 0.441 | 1.3 | 12 | 0 | 0 | wikictl log 14×/8s, wikictl ls 2×/1s, wikictl find 6×/1s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.369 | 1.3 | 12 | 0 | 0 | wikictl log 12×/6s, wikictl find 1×/0s, wikictl grep 1×/0s |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.181 | 0.9 | 25 | 0 | 0 | git log 10×/8s, git show 8×/0s, rg 1×/0s |
| sonnet | B2 | 3 | 0.92 | 0.00 | 0.665 | 4.7 | 31 | 0 | 1 | wikictl find 13×/16s, wikictl stat 9×/4s, wikictl cat 6×/3s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.292 | 1.3 | 25 | 0 | 0 | wikictl log 10×/7s, wikictl tree 2×/2s, wikictl find 12×/1s |
| sonnet | B2-lean | 3 | 0.96 | 0.67 | 0.237 | 1.2 | 20 | 0 | 0 | wikictl log 12×/6s, wikictl grep 5×/1s, wikictl ls 0×/0s |
| haiku | B1 | 3 | 0.96 | 0.67 | 0.119 | 1.2 | 26 | 0 | 0 | git log 15×/9s, git show 12×/0s |
| haiku | B2 | 3 | 1.00 | 0.00 | 0.218 | 2.1 | 44 | 0 | 3 | git log 16×/11s, wikictl grep 2×/1s, wikictl find 2×/1s |
| haiku | B2-best | 3 | 1.00 | 1.00 | 0.185 | 1.8 | 40 | 0 | 0 | wikictl log 11×/8s, wikictl ls 5×/5s, wikictl grep 4×/2s |
| haiku | B2-lean | 3 | 1.00 | 0.00 | 0.230 | 2.4 | 48 | 0 | 3 | git log 9×/6s, wikictl log 5×/4s, wikictl grep 4×/3s |

### P5

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B1 | 3 | 1.00 | 1.00 | 0.176 | 0.6 | 6 | 0 | 0 | git log 1×/0s, rg 2×/0s |
| opus | B2 | 3 | 1.00 | 1.00 | 0.315 | 1.6 | 9 | 0 | 0 | wikictl cat 162×/70s, wikictl ls 2×/3s, wikictl find 1×/1s |
| opus | B2-best | 3 | 1.00 | 1.00 | 0.296 | 0.7 | 8 | 0 | 0 | wikictl find 2×/0s, wikictl snapshot 1×/0s, rg 1×/0s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.163 | 0.6 | 6 | 0 | 0 | wikictl snapshot 1×/0s, rg 1×/0s |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.159 | 0.8 | 17 | 0 | 0 | git status 0×/0s, git log 2×/0s |
| sonnet | B2 | 3 | 1.00 | 1.00 | 0.238 | 1.3 | 23 | 0 | 0 | wikictl grep 12×/5s, wikictl cat 9×/4s, wikictl ls 1×/2s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.272 | 1.1 | 25 | 0 | 0 | wikictl grep 12×/2s, wikictl cat 13×/1s, wikictl find 3×/1s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.215 | 1.2 | 27 | 0 | 0 | wikictl grep 6×/1s, wikictl ls 1×/1s, wikictl cat 7×/1s |
| haiku | B1 | 3 | 1.00 | 1.00 | 0.128 | 1.1 | 29 | 0 | 0 | - |
| haiku | B2 | 3 | 0.97 | 0.67 | 0.132 | 1.4 | 24 | 0 | 0 | wikictl cat 15×/7s, wikictl grep 7×/4s, wikictl find 2×/2s |
| haiku | B2-best | 3 | 1.00 | 1.00 | 0.175 | 1.7 | 25 | 0 | 0 | wikictl cat 115×/12s, wikictl ls 1×/1s, wikictl grep 5×/1s |
| haiku | B2-lean | 3 | 0.97 | 0.67 | 0.112 | 1.1 | 22 | 0 | 0 | wikictl grep 7×/4s, wikictl cat 11×/1s, wikictl ls 1×/1s |

### P6

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B1 | 3 | 1.00 | 1.00 | 0.282 | 1.4 | 13 | 0 | 0 | rg 1537×/16s |
| opus | B2 | 3 | 1.00 | 1.00 | 0.586 | 2.1 | 22 | 0 | 0 | wikictl cat 78×/33s, wikictl grep 23×/9s, wikictl ls 1×/2s |
| opus | B2-best | 3 | 1.00 | 1.00 | 0.495 | 1.4 | 17 | 0 | 0 | wikictl cat 12×/1s, wikictl grep 4×/1s, wikictl find 1×/0s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.424 | 1.3 | 15 | 0 | 0 | wikictl cat 8×/1s, wikictl grep 3×/1s, wikictl ls 1×/1s |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.218 | 1.4 | 27 | 0 | 0 | - |
| sonnet | B2 | 3 | 1.00 | 1.00 | 0.386 | 3.1 | 35 | 0 | 0 | wikictl cat 155×/66s, wikictl grep 15×/9s, wikictl find 11×/4s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.529 | 2.7 | 40 | 0 | 0 | wikictl cat 22×/2s, wikictl grep 7×/2s, wikictl links 1×/1s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.333 | 1.6 | 35 | 0 | 0 | wikictl grep 14×/5s, wikictl cat 15×/2s, wikictl ls 0×/0s |
| haiku | B1 | 3 | 1.00 | 1.00 | 0.210 | 1.9 | 44 | 0 | 0 | - |
| haiku | B2 | 3 | 0.96 | 0.67 | 0.201 | 3.9 | 43 | 0 | 0 | wikictl cat 291×/124s, wikictl grep 10×/8s, wikictl find 10×/4s |
| haiku | B2-best | 3 | 0.96 | 0.67 | 0.229 | 2.9 | 43 | 0 | 0 | wikictl cat 603×/64s, wikictl grep 10×/5s, wikictl find 9×/1s |
| haiku | B2-lean | 3 | 1.00 | 1.00 | 0.217 | 2.4 | 58 | 0 | 0 | wikictl cat 298×/33s, wikictl grep 20×/10s, wikictl find 8×/1s |

### P7

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B1 | 3 | 1.00 | 1.00 | 0.591 | 1.8 | 16 | 0 | 0 | git log 2×/0s, rg 3×/0s |
| opus | B2 | 3 | 1.00 | 1.00 | 1.306 | 3.8 | 34 | 0 | 0 | wikictl cat 27×/13s, wikictl ls 4×/5s, wikictl grep 6×/3s |
| opus | B2-best | 3 | 1.00 | 1.00 | 1.029 | 2.8 | 24 | 0 | 0 | wikictl tree 2×/2s, wikictl ls 1×/1s, wikictl snapshot 2×/0s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.762 | 2.3 | 20 | 0 | 0 | wikictl ls 2×/2s, wikictl snapshot 2×/1s, wikictl find 0×/0s |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.692 | 4.0 | 41 | 0 | 0 | - |
| sonnet | B2 | 3 | 1.00 | 1.00 | 1.083 | 6.1 | 50 | 0 | 0 | wikictl cat 75×/31s, wikictl grep 31×/16s, wikictl find 21×/9s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.910 | 5.1 | 46 | 0 | 0 | wikictl grep 9×/2s, wikictl cat 14×/1s, wikictl tree 1×/1s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.842 | 4.4 | 39 | 0 | 0 | wikictl grep 10×/3s, wikictl ls 2×/2s, wikictl find 6×/1s |
| haiku | B1 | 3 | 0.45 | 0.33 | 0.252 | 2.6 | 33 | 0 | 0 | - |
| haiku | B2 | 3 | 0.18 | 0.00 | 0.331 | 10.3 | 41 | 0 | 0 | wikictl cat 1080×/456s, wikictl find 19×/8s, wikictl grep 5×/2s |
| haiku | B2-best | 3 | 0.45 | 0.33 | 0.327 | 4.1 | 37 | 0 | 0 | wikictl cat 264×/28s, wikictl find 17×/2s, wikictl grep 7×/1s |
| haiku | B2-lean | 3 | 0.12 | 0.00 | 0.259 | 3.5 | 37 | 0 | 0 | wikictl cat 383×/40s, wikictl ls 6×/3s, wikictl find 8×/1s |

### P8

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B0 | 3 | 0.00 | 0.00 | 0.361 | 1.4 | 16 | 0 | 0 | git status 1×/1s, git log 2×/0s, rg 1×/0s |
| opus | B1 | 3 | 1.00 | 1.00 | 1.046 | 3.3 | 31 | 0 | 0 | git pull 2×/1s, git push 2×/0s, git log 5×/0s |
| opus | B2 | 3 | 1.00 | 1.00 | 1.038 | 3.5 | 28 | 0 | 0 | wikictl cat 39×/17s, wikictl put 14×/16s, wikictl ls 4×/6s |
| opus | B2-best | 3 | 1.00 | 1.00 | 1.083 | 3.3 | 26 | 0 | 0 | wikictl put 15×/13s, wikictl cat 25×/3s, wikictl ls 3×/2s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 0.981 | 3.4 | 30 | 0 | 0 | wikictl put 15×/12s, wikictl ls 6×/6s, wikictl cat 7×/1s |
| sonnet | B0 | 3 | 0.00 | 0.00 | 0.248 | 1.9 | 18 | 0 | 0 | git status 1×/1s, git log 2×/0s, git remote 1×/0s |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.404 | 2.5 | 43 | 0 | 0 | git pull 2×/1s, git push 1×/0s, git log 3×/0s |
| sonnet | B2 | 3 | 1.00 | 1.00 | 0.497 | 3.0 | 34 | 0 | 0 | wikictl cat 30×/13s, wikictl put 11×/13s, wikictl tree 2×/1s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.464 | 2.4 | 32 | 0 | 0 | wikictl put 8×/6s, wikictl cat 19×/2s, wikictl tree 3×/2s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.392 | 2.7 | 36 | 0 | 0 | wikictl put 8×/7s, wikictl grep 9×/4s, wikictl cat 17×/2s |
| haiku | B0 | 3 | 0.00 | 0.00 | 0.273 | 2.9 | 40 | 0 | 0 | git log 3×/1s |
| haiku | B1 | 3 | 0.06 | 0.00 | 0.351 | 3.6 | 67 | 0 | 0 | git pull 2×/1s, git log 5×/0s, git push 1×/0s |
| haiku | B2 | 3 | 0.67 | 0.67 | 0.182 | 2.2 | 31 | 0 | 0 | wikictl cat 18×/7s, wikictl grep 3×/2s, wikictl put 1×/2s |
| haiku | B2-best | 3 | 0.49 | 0.00 | 0.225 | 2.4 | 40 | 0 | 0 | wikictl cat 22×/2s, wikictl put 3×/2s, wikictl grep 4×/1s |
| haiku | B2-lean | 3 | 0.33 | 0.33 | 0.332 | 4.5 | 52 | 0 | 1 | wikictl put 5×/4s, wikictl cat 27×/3s, wikictl grep 6×/2s |

### P9

| model | cond | n | score | success | USD | min | tool calls | timeouts | groups breaking rules | most time in (runs/seconds per group) |
|---|---|---|---|---|---|---|---|---|---|---|
| opus | B1 | 3 | 1.00 | 1.00 | 1.524 | 1.9 | 61 | 0 | 0 | git pull 10×/3s, git push 5×/1s, git log 15×/1s |
| opus | B2 | 3 | 1.00 | 1.00 | 2.293 | 2.8 | 60 | 0 | 0 | wikictl put 30×/35s, wikictl cat 56×/25s, wikictl ls 8×/8s |
| opus | B2-best | 3 | 1.00 | 1.00 | 2.345 | 2.9 | 60 | 0 | 0 | wikictl put 29×/28s, wikictl cat 42×/4s, wikictl find 12×/3s |
| opus | B2-lean | 3 | 1.00 | 1.00 | 1.480 | 2.0 | 45 | 0 | 0 | wikictl put 20×/37s, wikictl ls 8×/8s, wikictl cat 21×/3s |
| sonnet | B1 | 3 | 1.00 | 1.00 | 0.646 | 1.8 | 69 | 0 | 0 | git pull 9×/3s, git push 4×/1s, git log 5×/0s |
| sonnet | B2 | 3 | 1.00 | 1.00 | 0.774 | 1.8 | 66 | 0 | 0 | wikictl put 19×/32s, wikictl cat 27×/14s, wikictl find 16×/6s |
| sonnet | B2-best | 3 | 1.00 | 1.00 | 0.864 | 2.0 | 69 | 0 | 0 | wikictl put 20×/18s, wikictl cat 25×/5s, wikictl grep 7×/1s |
| sonnet | B2-lean | 3 | 1.00 | 1.00 | 0.670 | 2.2 | 66 | 0 | 0 | wikictl put 21×/37s, wikictl cat 21×/4s, wikictl grep 14×/3s |
| haiku | B1 | 3 | 1.00 | 0.00 | 0.353 | 1.8 | 86 | 0 | 0 | git push 6×/2s, git pull 6×/2s, git add 6×/0s |
| haiku | B2 | 3 | 1.00 | 0.67 | 0.452 | 2.7 | 87 | 0 | 0 | wikictl put 24×/56s, wikictl cat 44×/19s, wikictl ls 6×/6s |
| haiku | B2-best | 3 | 1.00 | 1.00 | 0.391 | 2.0 | 63 | 0 | 0 | wikictl put 21×/43s, wikictl cat 33×/5s, wikictl ls 2×/1s |
| haiku | B2-lean | 3 | 0.94 | 0.00 | 0.509 | 4.0 | 88 | 0 | 1 | wikictl put 35×/42s, wikictl cat 53×/7s, wikictl ls 5×/5s |

### Difference from B1 (score, USD ratio, time ratio)

| model | task | B2 | B2-best | B2-lean |
|---|---|---|---|---|
| opus | L1 | 0.00 / ×1.49 / ×1.39 | 0.00 / ×1.48 / ×1.11 | 0.00 / ×1.01 / ×1.04 |
| opus | L2 | 0.00 / ×2.33 / ×2.07 | 0.00 / ×2.31 / ×1.92 | 0.00 / ×1.32 / ×1.43 |
| opus | P2 | 0.00 / ×2.00 / ×1.92 | 0.00 / ×1.71 / ×1.20 | 0.00 / ×1.15 / ×1.37 |
| opus | P3K | 0.00 / ×1.36 / ×1.30 | 0.00 / ×1.03 / ×0.86 | 0.00 / ×0.94 / ×0.92 |
| opus | P3M | 0.00 / ×2.07 / ×1.13 | 0.00 / ×1.43 / ×0.59 | 0.00 / ×1.17 / ×0.70 |
| opus | P4 | -0.12 / ×5.46 / ×6.14 | 0.00 / ×1.50 / ×1.22 | 0.00 / ×1.25 / ×1.22 |
| opus | P5 | 0.00 / ×1.79 / ×2.78 | 0.00 / ×1.68 / ×1.25 | 0.00 / ×0.93 / ×1.09 |
| opus | P6 | 0.00 / ×2.08 / ×1.54 | 0.00 / ×1.75 / ×1.04 | 0.00 / ×1.50 / ×0.94 |
| opus | P7 | 0.00 / ×2.21 / ×2.07 | 0.00 / ×1.74 / ×1.53 | 0.00 / ×1.29 / ×1.26 |
| opus | P8 | 0.00 / ×0.99 / ×1.05 | 0.00 / ×1.04 / ×1.00 | 0.00 / ×0.94 / ×1.02 |
| opus | P9 | 0.00 / ×1.50 / ×1.46 | 0.00 / ×1.54 / ×1.54 | 0.00 / ×0.97 / ×1.05 |
| sonnet | L1 | 0.00 / ×1.22 / ×1.81 | 0.00 / ×1.40 / ×1.57 | 0.00 / ×0.90 / ×1.94 |
| sonnet | L2 | 0.00 / ×1.22 / ×1.41 | 0.00 / ×1.73 / ×1.41 | 0.00 / ×1.53 / ×1.72 |
| sonnet | P2 | 0.00 / ×1.99 / ×1.72 | 0.00 / ×2.76 / ×2.04 | 0.00 / ×1.57 / ×1.74 |
| sonnet | P3K | 0.00 / ×1.65 / ×1.93 | 0.00 / ×0.98 / ×1.00 | 0.00 / ×1.47 / ×1.78 |
| sonnet | P3M | 0.00 / ×1.49 / ×1.38 | 0.00 / ×1.16 / ×0.87 | 0.00 / ×1.28 / ×1.03 |
| sonnet | P4 | -0.08 / ×3.68 / ×4.96 | 0.00 / ×1.61 / ×1.32 | -0.04 / ×1.31 / ×1.28 |
| sonnet | P5 | 0.00 / ×1.49 / ×1.54 | 0.00 / ×1.71 / ×1.28 | 0.00 / ×1.35 / ×1.46 |
| sonnet | P6 | 0.00 / ×1.77 / ×2.31 | 0.00 / ×2.43 / ×1.97 | 0.00 / ×1.53 / ×1.18 |
| sonnet | P7 | 0.00 / ×1.57 / ×1.52 | 0.00 / ×1.32 / ×1.27 | 0.00 / ×1.22 / ×1.09 |
| sonnet | P8 | 0.00 / ×1.23 / ×1.20 | 0.00 / ×1.15 / ×0.99 | 0.00 / ×0.97 / ×1.08 |
| sonnet | P9 | 0.00 / ×1.20 / ×0.99 | 0.00 / ×1.34 / ×1.08 | 0.00 / ×1.04 / ×1.17 |
| haiku | L1 | 0.00 / ×1.66 / ×1.40 | 0.00 / ×1.07 / ×1.05 | 0.00 / ×0.97 / ×1.00 |
| haiku | L2 | -0.02 / ×1.16 / ×1.18 | 0.00 / ×0.95 / ×0.83 | 0.00 / ×1.11 / ×0.97 |
| haiku | P2 | 0.00 / ×1.29 / ×1.21 | 0.00 / ×1.14 / ×1.01 | 0.00 / ×1.14 / ×1.22 |
| haiku | P3K | +0.00 / ×1.89 / ×8.54 | -0.01 / ×1.75 / ×1.49 | -0.12 / ×1.21 / ×1.20 |
| haiku | P3M | 0.00 / ×1.68 / ×4.35 | -0.01 / ×1.58 / ×1.39 | 0.00 / ×1.32 / ×1.44 |
| haiku | P4 | +0.04 / ×1.83 / ×1.74 | +0.04 / ×1.55 / ×1.46 | +0.04 / ×1.93 / ×1.98 |
| haiku | P5 | -0.03 / ×1.02 / ×1.25 | 0.00 / ×1.36 / ×1.51 | -0.03 / ×0.87 / ×1.02 |
| haiku | P6 | -0.04 / ×0.95 / ×2.05 | -0.04 / ×1.09 / ×1.54 | 0.00 / ×1.03 / ×1.29 |
| haiku | P7 | -0.27 / ×1.32 / ×3.92 | 0.00 / ×1.30 / ×1.56 | -0.33 / ×1.03 / ×1.32 |
| haiku | P8 | +0.60 / ×0.52 / ×0.62 | +0.43 / ×0.64 / ×0.66 | +0.27 / ×0.95 / ×1.24 |
| haiku | P9 | 0.00 / ×1.28 / ×1.52 | 0.00 / ×1.11 / ×1.15 | -0.06 / ×1.44 / ×2.27 |

