# wikictl-eval

[English](README.md)

[wikictl](https://github.com/roamer7038/wikictl) が、エージェントの作業の品質・費用・速度（QCD）をどれだけ変えるかを測るための課題、実行環境、採点のスクリプト。目的と判断事項は [roamer7038/wikictl#184](https://github.com/roamer7038/wikictl/issues/184) にある。

- 結果: [results/main.md](results/main.md)（本番、2026-09-17）

## 問い

1. 情報がローカルにある場合（clone を標準のコマンドで読む、または wikictl で読む）と、ない場合（モデルの知識だけ）で、結果はどれだけ違うか。
2. リモートのリポジトリを実質ローカルのように扱う wikictl（B2）が、clone と標準のコマンド（B1）と同等以上になるには、何が要るか。

## 条件

| 条件 | 文書への経路 |
|---|---|
| B0 | 使わない（モデルの知識で答える）。P8 だけは clone を読み、チームの wiki がない |
| B1 | clone ＋ `rg`・`cat`・`git`、Claude Code 組み込みの Read・Grep |
| B2 | wikictl v0.4.1 ＋ [wikictl-claude-plugin](https://github.com/roamer7038/wikictl-claude-plugin) b5763e8 |
| B2-trigger | B2 のスキルの説明文を広げ、wikictl を使う課題なら読まれるようにしたもの |
| B2-help | B2 の wikictl のトップのヘルプに、多数のファイルの読み方を加えたもの |
| B2-nofetch | B2 で、文書の読み取りに `--no-fetch` を付けたもの |
| B2-skill | 説明文を広げ、多数のファイルの読み方を加えたスキル |
| B2-proto | 試作の wikictl（`meta`・`log`・`show`・`snapshot`）＋ 検索の拡張 `wikictl-search` ＋ その使い分けを書いたスキル |
| B2-best | B2-proto ＋ ヘルプの追加 ＋ 読み取りの前の fetch を 300 秒省く |
| B2-lean | B2-best と同じ wikictl と拡張 ＋ コマンドの表だけの短いスキル（22 行） |

課題文は条件の間で同じ。違うのは「環境」の節（[`tasks/v2/env-*.md`](tasks/v2/) と `tasks/v2/src-*.md`）だけ。wikictl の試作は v0.4.1 への patch（[`docker/proto/`](docker/proto/)）、スキルの変形は [`docker/plugins/`](docker/plugins/)、検索の拡張は [`docker/ext/`](docker/ext/) にある。

## 題材

固定したコミットの実在のリポジトリ。

| リポジトリ | コミット | 使う情報 |
|---|---|---|
| [kubernetes/website](https://github.com/kubernetes/website) | `aa4e9e6` | feature gate のページ（英語 487、中国語訳 466）の `stages`、文書の本文とリンク、履歴 |
| [kubernetes/enhancements](https://github.com/kubernetes/enhancements) | `766deac` | KEP の `kep.yaml`（owning-sig、stage、milestone、feature-gates） |
| [mdn/content](https://github.com/mdn/content) | `8e307de` | ページ 14,661 の frontmatter（`status`、`page-type`、`slug`）、本文の参照、履歴 |

P8 と P9 で書き込むチームの wiki は、[`gen/real.py`](gen/real.py) が作る小さな wiki。

## 課題

課題文は日本語。正解は [`gen/tasks.py`](gen/tasks.py) が固定したコミットから計算する（`data/tasks/truth.json`）。

| ID | 型 | 内容 | 採点 |
|---|---|---|---|
| L1 | 値 | feature gate 14 問（中国語訳が古いままの gate の v1.37 での段階、最近と古くに入った段階の版、存在しない gate） | 正答・古い値・不明・誤り |
| L2 | 値 | MDN のページ 14 件の `status`（2026 年に外れた・加わった・変わらない、存在しないページ） | 同上 |
| P2 | 全文検索 | `content/en/docs` の中で、あるフラグに触れているただ 1 つのページ（8 問） | 正答 |
| P3K・P3M | 集計 | 条件に当てはまる feature gate（19・18・18 件）、MDN のページ（60・9・58 件） | F1 |
| P4 | 履歴 | gate のページに stable の段が加わった日付、MDN のページから experimental が外れた日付（8 問） | 正答（作成日・コミット日・main への取り込み日を受け付ける） |
| P5 | 曖昧な表現 | 名前を示さない日本語の説明（5）と英語の言い換え（5）から gate を特定。問題文は Opus で作り、別の呼び出しで一意に特定できたものだけを使う（[`gen/paraphrase.py`](gen/paraphrase.py)） | 正答 |
| P6 | 多段の参照 | gate のページが最初にリンクする文書の title、gate を導入した KEP の SIG が持つ他の KEP、MDN のページが最初に参照する API の status（9 問） | 正答・F1 |
| P7 | リポジトリ間の照合 | KEP と文書で stable の版が異なる gate、KEP が stable なのに文書に stable の段がない gate | F1 |
| P8 | 別のセッションで続ける | 1 回目の課題文でだけチームの判断を伝え、2 回目（会話も作業ディレクトリも引き継がない）でそれと文書を合わせて答える | 2 回目の F1 |
| P9 | 同時に書く | 3 エージェントが同時に 5 件ずつ gate を調べてページを作り、同じ一覧に行を加える | 欠け・事実の誤り・重複・既存の行の消失・並び順 |

成功は、全問正答（F1 ≥ 0.95 を正答）で、かつ課題文の規則に反しなかったこと。規則違反は、B2 系で wikictl のミラーを git で直接読むこと、git でリモートに直接アクセスすることなどを数える（[`grade/score.py`](grade/score.py)）。

## 指標

- 品質（Q）: 点（問いごとの 1/0 または F1 の平均）と成功。
- 費用（C）: `claude -p` の `result` イベントの `modelUsage` のトークン数に、[`grade/prices.json`](grade/prices.json) の単価を掛けた USD。
- 速度（D）: セッションの実時間。P9 は 3 エージェントのうち最も長いもの。
- 補助: ツールの呼び出し（トランスクリプトの時刻から所要時間と出力の大きさ）、ラッパーが記録した `wikictl`・`git`・`rg` の実行、スキルの読み込み、試作のコマンドの使用、規則違反。

## 実行環境

- Docker: 1 セッションを 1 コンテナ（2 CPU、6 GB）で動かす。イメージ（[`docker/agent.Dockerfile`](docker/agent.Dockerfile)）は Claude Code 2.1.273、wikictl v0.4.1（リリースのバイナリをチェックサムで検証）と試作、プラグインの変形、`wikictl-search` と多言語の埋め込みモデル（paraphrase-multilingual-MiniLM-L12-v2）を含む。
- リモート: 固定したリポジトリとチームの wiki を git daemon のコンテナで配る。遅延なし（`git0`）と、送るパケットごとに 40 ms の遅延（`git40`）の 2 つ。
- 事前準備: B1 の clone、B2 系の wikictl のミラー、`wikictl-search` の索引は、一度作ったものをセッションごとに写す。どの条件も数百 MB の取得から始まらない。
- 分離: セッションが見えるのは、そのセッションの HOME・作業ディレクトリ・文書の clone だけ。利用者の CLAUDE.md、メモリ、プラグイン、MCP サーバは読み込まれない。ツールは Bash・Read・Write・Edit・Glob・Grep（B2 系は Skill も）。
- 利用制限: セッションが利用制限で終わったら、そのグループを退避して、メッセージの解除時刻まで待ってやり直す。

## 再現の手順

必要なもの: Linux、Docker、Python 3.12 と PyYAML、git、curl、Claude Code（トークンの作成に使う）。

```sh
./setup.sh                          # 固定したリポジトリ（data/remotes）と合成の題材
python3 gen/real.py && python3 gen/tasks.py   # 問題と正解（data/tasks）
docker build -t wikictl-eval-agent:v4 -f docker/agent.Dockerfile docker
docker build -t wikictl-eval-gitserver:dev -f docker/gitserver.Dockerfile docker
claude setup-token                  # 表示されたトークンを次のファイルに保存する
mkdir -p ~/.config/wikictl-eval && ( umask 077; cat > ~/.config/wikictl-eval/oauth-token )

export EVAL_IMAGE=wikictl-eval-agent:v4
harness/eval.py run --task P3K --cond B2-lean --model sonnet --rep 1          # 1 グループ
harness/eval.py batch --tasks L1,L2,P2,P3K,P3M,P4,P5,P6,P7,P8,P9 \
  --conds B0,B1,B2,B2-best,B2-lean --models opus,sonnet,haiku --reps 3 --label main
grade/score.py ../wikictl-eval-runs/*-main > results/main-scores.jsonl
grade/qcd.py results/main-scores.jsonl > results/main-qcd.md
```

グループは `../wikictl-eval-runs/`（または `$EVAL_RUNS`）に書く。Claude Code は上位のディレクトリにある Git リポジトリの git status をシステムプロンプトに入れるので、どの Git リポジトリの中でもない場所にする。このディレクトリにはトランスクリプトが残り、被験のコンテナには認証トークンが渡るので、公開しない。

以前の版の実行環境（合成の題材の T1〜T4、kubernetes と mdn の K1・M1・K3・M3・K5・W を unshare で隔離して動かすもの）は `harness/run.py`・`harness/real.py`・`harness/jail.sh` に残してある。

## ライセンス

MIT。題材のリポジトリはそれぞれのライセンスに従う（kubernetes/website は CC-BY-4.0、kubernetes/enhancements は Apache-2.0、mdn/content の文章は CC-BY-SA-2.5）。
