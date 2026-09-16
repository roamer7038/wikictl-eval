# wikictl-eval

[English](README.md)

[wikictl](https://github.com/roamer7038/wikictl) が、エージェントの作業の品質・費用・速度をどれだけ変えるかを測るための課題、実行環境、採点のスクリプト。目的と判断事項は [roamer7038/wikictl#184](https://github.com/roamer7038/wikictl/issues/184) にある。

## 条件

| 条件 | wiki への経路 |
|---|---|
| B0 | wiki を使わない |
| B1 | wiki を clone してあり、`rg`・`cat`・`git` で読み書きする |
| B2 | wikictl と [wikictl-claude-plugin](https://github.com/roamer7038/wikictl-claude-plugin) を使う |

課題文は条件の間で同じにしてある。違うのは「環境」の節（[`tasks/env-B0.md`](tasks/env-B0.md) など）だけ。

## 課題

| ID | 課題 | 条件 | 正解 |
|---|---|---|---|
| T1 | 値を思い出す: 72 ページの wiki と構成ファイル（`infra/`）から 10 問に答える。うち 6 問は、古い値が議事録と履歴に残っている | B0 B1 B2 | 生成した世界モデルの現在の値 |
| T2 | 別のセッションで続ける: 重ね合わせで決まる配置の値を、1 回目は 4 プロジェクト、2 回目は全 8 プロジェクト（24 サービス）について求める。2 回目は会話も作業ディレクトリも引き継がない | B0 B1 B2 | 重ね合わせの規則で計算した値 |
| T3 | 複数のエージェントが同時に書く: 3 エージェントが同時に 5 件ずつ障害のページを作り、同じ一覧のページに行を加える | B1 B2 | 15 件のページと行 |
| T4 | 大きな wiki: T1 と同じ質問を 1,012 ページの wiki で | B1 B2 | T1 と同じ |

題材はすべて [`gen/`](gen/) で生成する（seed は固定）。公開していない wiki は使わない。

## 指標

- 品質: T1/T4 は正答・古い値・不明・誤りの数。T2 はフィールドの正答数。T3 は欠けたページと行、重複した行、既存の行の消失、並び順。書き込みには wikictl v0.4.1 の `lint` をかける。
- 費用: `claude -p` の `result` イベントの `modelUsage` のトークン数に、[`grade/prices.json`](grade/prices.json) の単価を掛けた USD。
- 速度: セッションの実時間、ターン数、ラッパーで記録した `wikictl`・`git`・`rg` の呼び出し回数と出力の大きさ。

## 実行環境

- 版: wikictl v0.4.1（リリースのバイナリをチェックサムで検証）、プラグイン b5763e8、Claude Code 2.1.273。実際の値は `build/versions.tsv` に記録する。
- セッションは `claude -p` で起動し、HOME・`CLAUDE_CONFIG_DIR`・PATH をセッションごとに分ける。利用者の CLAUDE.md、メモリ、プラグイン、MCP サーバは読み込まれない。B2 だけ `--plugin-dir` でプラグインを読み込む。組み込みのスキルは全条件で同じ。
- ツールは Bash・Read・Write・Edit・Glob・Grep（B2 は Skill も）。サブエージェントと Web のツールは使わせない。
- wiki のリモートはローカルの bare リポジトリなので、ネットワーク越しの fetch の待ち時間は含まない。
- コマンドは PATH に置いたラッパーで、親プロセスと一緒に記録する。Claude Code 自身が実行する git は、エージェントの呼び出しに数えない。Read・Grep・Glob はラッパーを通らないので、トランスクリプトからツールの呼び出しとして数える。
- セッションはサンドボックスで隔離していない。課題文で作業ディレクトリの外を読まないように指示しているだけ。

## 再現の手順

必要なもの: Linux、Python 3.12、git、ripgrep、jq、curl、Claude Code。

```sh
./setup.sh                                   # build/ に wikictl とプラグイン、data/ に題材
claude setup-token                           # 表示されたトークンを次のファイルに保存する
mkdir -p ~/.config/wikictl-eval && ( umask 077; cat > ~/.config/wikictl-eval/oauth-token )

harness/run.py --task T1 --cond B2 --model sonnet --rep 1           # 1 グループ
harness/batch.py --models opus,sonnet,haiku --reps 3                # 全課題 × 全条件
grade/grade.py ../wikictl-eval-runs/*-r[123] > results/raw/main.jsonl
grade/report.py results/raw/main.jsonl > results/main.md
```

グループは `../wikictl-eval-runs/`（または `$EVAL_RUNS`）に書く。Claude Code は、上位のディレクトリにある Git リポジトリの git status をシステムプロンプトに入れるので、どの Git リポジトリの中でもない場所にする。このディレクトリにはトランスクリプトが残り、被験エージェントの環境には認証トークンが入っているので、公開しない。

## ライセンス

MIT
