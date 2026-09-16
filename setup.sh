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

{
  echo "wikictl	$WIKICTL_REF	$(sha256sum build/bin/wikictl | cut -d' ' -f1)"
  echo "plugin	$PLUGIN_REF	$(git -C build/plugin rev-parse HEAD)"
  echo "claude	$(claude --version | head -1)"
  for n in small big; do echo "wiki-$n	$(git -C data/$n/wiki.git rev-parse HEAD)"; done
} | tee build/versions.tsv
build/bin/wikictl version
