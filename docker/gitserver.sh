#!/bin/sh
# gitserver.sh [delay-ms]: add the delay to every packet this container
# sends (so a round trip takes that long), then serve /srv/git as uid 1000.
set -eu
if [ "${1:-0}" != 0 ]; then
  tc qdisc add dev eth0 root netem delay "${1}ms"
fi
exec setpriv --reuid=1000 --regid=1000 --clear-groups \
  git -c safe.directory='*' daemon --reuseaddr --export-all --enable=receive-pack \
  --base-path=/srv/git --informative-errors /srv/git
