# wikictl-eval

[English](README.md)

[wikictl](https://github.com/roamer7038/wikictl) が、エージェントの作業の品質・費用・速度をどれだけ変えるかを測るための課題、実行環境、採点のスクリプト。目的と判断事項は [roamer7038/wikictl#184](https://github.com/roamer7038/wikictl/issues/184) にある。

## 条件

| 条件 | 文書のリポジトリへの経路 | チームの wiki（K5・W） |
|---|---|---|
| B0 | 使わない（モデルの知識だけで答える）。K5 だけは B1 と同じ clone を読む | なし |
| B1 | clone してあり、`rg`・`cat`・`git` で読む | clone してあり、`git` で commit・push する |
| B2 | wikictl（リポジトリごとのプロファイル）と [wikictl-claude-plugin](https://github.com/roamer7038/wikictl-claude-plugin) | wikictl |

課題文は条件の間で同じ。違うのは「環境」の節（[`tasks/env-real-B0.md`](tasks/env-real-B0.md) と `tasks/src-*.md`）だけ。

## 題材

固定したコミットの実在のリポジトリを使う。

| リポジトリ | コミット | 規模 |
|---|---|---|
| [kubernetes/website](https://github.com/kubernetes/website) | `aa4e9e6`（2026-09-16） | .md 8,224、feature gate のページ 487（英語）・466（中国語訳） |
| [mdn/content](https://github.com/mdn/content) | `8e307de`（2026-09-16） | ページ 14,661（57MB） |

K5 と W で書き込むチームの wiki は、[`gen/real.py`](gen/real.py) が作る小さな wiki（調べた feature gate が 3 件記録されている）。

## 課題

課題文は日本語。正解はすべて、固定したコミットの frontmatter から [`gen/real.py`](gen/real.py) が計算する。

| ID | 課題 | 条件 | 正解と採点 |
|---|---|---|---|
| K1 | feature gate について 12 問に答える。4 問は中国語訳が古い段階のままの gate の v1.37 での段階、4 問は v1.36・v1.37 に入った段階の版、4 問は v1.30 以前に入った段階の版 | B0 B1 B2 | 英語版の `stages`。正答・古い値（中国語訳の値）・不明・誤り |
| M1 | MDN のページ 12 件の `status` を答える。5 件は 2026 年に値が外れた、4 件は加わった、3 件は 2026 年に変わっていない | B0 B1 B2 | `status`。正答・古い値（2026 年より前の値）・不明・誤り |
| K3 | 「v1.37 で beta に入った gate」など 3 つの条件に当てはまる gate をすべて挙げる（19・18・18 件） | B0 B1 B2 | 集合の F1 |
| M3 | 「status に experimental を含む CSS プロパティ」など 3 つの条件に当てはまるページをすべて挙げる（60・9・58 件） | B0 B1 B2 | 集合の F1 |
| K5 | 別のセッションで続ける。1 回目は v1.37 で stable に入った gate を挙げ、次のセッションのために記録する。2 回目は会話も作業ディレクトリも引き継がずに、v1.36・v1.37 についての別の 3 つの条件に答える | B0 B1 B2 | 集合の F1、2 回目の費用、wiki への書き込み |
| W | 3 エージェントが同時に 5 件ずつ feature gate を調べ、ページを作り、同じ一覧のページに行を加える | B1 B2 | 欠けたページと行、事実の誤り、重複、既存の行の消失、並び順、`lint` |

合成した題材の課題（T1〜T4、[`gen/build.py`](gen/build.py)）も残してある。答えの場所が明らかで差が出なかったので、既定の実行からは外している。

## 指標

- 品質: 上の表の採点。書き込みには wikictl v0.4.1 の `lint` をかける。
- 費用: `claude -p` の `result` イベントの `modelUsage` のトークン数に、[`grade/prices.json`](grade/prices.json) の単価を掛けた USD。`stream-json` の途中のイベントは出力トークンを少なく記録するので使わない。
- 速度: セッションの実時間、ターン数、ツールの呼び出し回数、ラッパーで記録した `wikictl`・`git`・`rg` の呼び出し回数と出力の大きさ。

## 実行環境

- 版: wikictl v0.4.1（リリースのバイナリをチェックサムで検証）、プラグイン b5763e8、Claude Code 2.1.273。実際の値は `build/versions.tsv` に記録する。
- 隔離: セッションは `unshare -Urmpf` の名前空間で [`harness/jail.sh`](harness/jail.sh) を通して動く。`/home`・`/tmp`・`/mnt` は空になり、見えるのは次のものだけ。
  - 読み書きできる: そのグループのディレクトリ。
  - 読むだけ: Claude Code、wikictl、プラグイン。B1・B2 と K5 の B0 では、固定した文書のリポジトリも見える。
  - PID 名前空間も分けるので、`/proc` からほかのプロセスのファイルシステムにたどり着けない。
- 設定の分離: HOME・`CLAUDE_CONFIG_DIR`・PATH をセッションごとに分ける。利用者の CLAUDE.md、メモリ、プラグイン、MCP サーバは読み込まれない。B2 だけ `--plugin-dir` でプラグインを読み込む。組み込みのスキルは全条件で同じ。
- ツール: Bash・Read・Write・Edit・Glob・Grep（B2 は Skill も）。サブエージェントと Web のツールは使わせない。
- 事前準備: B1 の clone（`--shared`）と B2 の wikictl のミラーは、セッションの前に用意する。ミラーは一度作ったものをハードリンクで写すので、どちらの条件も数百 MB の取得から始まることはない。リモートはローカルのリポジトリなので、ネットワーク越しの fetch の待ち時間は含まない。
- ログ: コマンドは PATH に置いたラッパーで、親プロセスと一緒に記録する。Claude Code 自身が実行する git は数えない。Read・Grep・Glob はラッパーを通らないので、トランスクリプトからツールの呼び出しとして数える。

## 再現の手順

必要なもの:
- Linux（非特権のユーザ名前空間が使えること）と util-linux の `unshare`
- Python 3.12 と PyYAML
- git、ripgrep、jq、curl、Claude Code

```sh
./setup.sh                                   # build/ に wikictl とプラグイン、data/ に固定したリポジトリと問題
claude setup-token                           # 表示されたトークンを次のファイルに保存する
mkdir -p ~/.config/wikictl-eval && ( umask 077; cat > ~/.config/wikictl-eval/oauth-token )

harness/run.py --task K3 --cond B2 --model sonnet --rep 1           # 1 グループ
harness/batch.py --models opus,sonnet,haiku --reps 3                # 全課題 × 全条件
grade/grade.py ../wikictl-eval-runs/*-r[123] > results/raw/main.jsonl
grade/report.py results/raw/main.jsonl > results/main.md
```

グループは `../wikictl-eval-runs/`（または `$EVAL_RUNS`）に書く。Claude Code は上位のディレクトリにある Git リポジトリの git status をシステムプロンプトに入れるので、どの Git リポジトリの中でもない場所にする。このディレクトリにはトランスクリプトが残り、被験エージェントの環境には認証トークンが入っているので、公開しない。

## ライセンス

MIT。題材のリポジトリはそれぞれのライセンスに従う（kubernetes/website は CC-BY-4.0、mdn/content は CC-BY-SA-2.5 と MIT/CC0 のコード例）。
