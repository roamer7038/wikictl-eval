#!/bin/bash
# setup.sh: fetch the pinned wikictl and plugin into build/ and generate data/.
set -euo pipefail
cd "$(dirname "$0")"
WIKICTL_REF=v0.4.1
PLUGIN_REF=b5763e8

mkdir -p build/bin
base=https://github.com/roamer7038/wikictl/releases/download/$WIKICTL_REF
asset=wikictl_linux_$(uname -m)
curl -fsSL -o build/checksums.txt "$base/checksums.txt"
curl -fsSL -o "build/$asset" "$base/$asset"
(cd build && grep " $asset\$" checksums.txt | sha256sum -c --quiet -)
install -m 755 "build/$asset" build/bin/wikictl

if [ ! -d build/plugin ]; then
  git clone -q https://github.com/roamer7038/wikictl-claude-plugin.git build/plugin
fi
git -C build/plugin -c advice.detachedHead=false checkout -q "$PLUGIN_REF"

python3 gen/build.py data

# The documentation repositories at the pinned commits, with their history,
# as read-only bare repositories whose only branch is main.
pin() {
  local name=$1 url=$2 sha=$3 dir=data/remotes/$1.git
  if [ ! -d "$dir" ]; then
    git clone -q --bare --single-branch --no-tags "$url" "$dir"
    git -C "$dir" update-ref refs/heads/main "$sha"
    git -C "$dir" symbolic-ref HEAD refs/heads/main
    git -C "$dir" for-each-ref --format='%(refname)' | grep -vx refs/heads/main | xargs -r -n1 git -C "$dir" update-ref -d
    git -C "$dir" remote remove origin
    git -C "$dir" reflog expire --expire=now --all
    git -C "$dir" -c gc.auto=0 gc -q --prune=now
    chmod -R a-w "$dir"
  fi
  [ "$(git -C "$dir" rev-parse HEAD)" = "$sha" ]
}
mkdir -p data/remotes
pin k8s-website https://github.com/kubernetes/website.git aa4e9e6dee49106155072a44ef997b91722243ec
pin mdn-content https://github.com/mdn/content.git 8e307de115d41e9214fcacbd7fe89532756816b4
python3 gen/real.py

{
  echo "wikictl	$WIKICTL_REF	$(sha256sum build/bin/wikictl | cut -d' ' -f1)"
  echo "plugin	$PLUGIN_REF	$(git -C build/plugin rev-parse HEAD)"
  echo "claude	$(claude --version | head -1)"
  for n in small big; do echo "wiki-$n	$(git -C data/$n/wiki.git rev-parse HEAD)"; done
  for n in k8s-website mdn-content; do echo "$n	$(git -C data/remotes/$n.git rev-parse HEAD)"; done
  echo "notes-wiki	$(git -C data/real/notes-wiki.git rev-parse HEAD)"
} | tee build/versions.tsv
build/bin/wikictl version
