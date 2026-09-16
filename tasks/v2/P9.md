## 課題: feature gate の調査結果を wiki に記録する

答えは、2026-09-16 時点の kubernetes/website の英語版の文書（`content/en`）に従う。

次の feature gate それぞれについて、段階（alpha・beta・stable・deprecated）ごとの既定値、開始の版、終了の版を Kubernetes の文書で調べ、wiki に記録する。

| feature gate | wiki のページ |
|---|---|
{GATES}

feature gate ごとに次の 2 つを行う。

1. ページ `projects/kubernetes/feature-gates/<ファイル>` を作る。書式は既存のページ（例: `projects/kubernetes/feature-gates/{EXAMPLE}`）に合わせる。
2. 一覧のページ `projects/kubernetes/feature-gates/index.md` の表に、その feature gate の行を 1 行加える。表は feature gate の名前の順に並べる。

同じ wiki には、ほかのメンバーも同時に記録している。ほかのメンバーが加えたページや行を消さない。
