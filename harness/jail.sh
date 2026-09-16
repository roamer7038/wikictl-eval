#!/bin/sh
# jail.sh <workdir> <rw-dir>... -- <ro-path>... -- <command>...
#
# Run command in a user and mount namespace (started by run.py with
# "unshare -Urm") where /home, /tmp and /mnt are empty except for the given
# paths, which keep their own names: <rw-dir> read-write, <ro-path> (a file
# or directory) read-only. The agent then cannot read the answers, the
# pinned repositories' other copies or anything else of the host user.
set -eu
work=$1; shift
stage=/tmp/.jail-host
mount -t tmpfs tmpfs /tmp
mkdir -p "$stage"
mount --rbind / "$stage"
mount -t tmpfs tmpfs /home
mount -t tmpfs tmpfs /mnt
bind() { # bind <mode> <path>
  if [ -d "$stage$2" ]; then mkdir -p "$2"; else mkdir -p "$(dirname "$2")"; : > "$2"; fi
  mount --rbind "$stage$2" "$2"
  if [ "$1" = ro ]; then mount -o remount,bind,ro "$2"; fi
}
mode=rw
while [ $# -gt 0 ]; do
  if [ "$1" = -- ]; then
    shift
    if [ $mode = ro ]; then break; fi
    mode=ro
    continue
  fi
  bind $mode "$1"
  shift
done
umount -l "$stage"
rmdir "$stage"
chmod 1777 /tmp
cd "$work"
exec "$@"
