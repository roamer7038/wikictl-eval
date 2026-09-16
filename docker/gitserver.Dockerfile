# Serves the pinned repositories and the per-group wikis with git daemon,
# optionally behind a network delay added by tc netem.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -q && apt-get install -qy --no-install-recommends git iproute2 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN usermod -l git -d /srv/git -m ubuntu && groupmod -n git ubuntu
COPY gitserver.sh /usr/local/bin/gitserver.sh
ENTRYPOINT ["/usr/local/bin/gitserver.sh"]
