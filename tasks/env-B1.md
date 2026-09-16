## 環境

- 作業ディレクトリ: 現在のディレクトリ（`{WORK}`）
- 知識の置き場: チームの wiki（Markdown の Git リポジトリ）を `{WIKI_DIR}` に clone してある（環境変数 `WIKI_DIR`）。読む前に `git -C "$WIKI_DIR" pull` で最新にし、`rg`・`cat`・`git log` などで読む。書くときは commit して push する。
- 使ってよいコマンド: 標準的な Unix コマンド（`ls`、`cat`、`rg`、`grep`、`sed`、`awk`、`jq` など）と `git`
