# The image each agent session runs in.
FROM golang:1.26-bookworm AS wikictl-proto
ARG WIKICTL_REF=v0.4.1
RUN git clone -q https://github.com/roamer7038/wikictl.git /src \
 && git -C /src -c advice.detachedHead=false checkout -q "$WIKICTL_REF"
COPY proto/wikictl.patch proto/help.patch /tmp/
# Three prototypes of v0.4.1: the help of reading many files (help), the new
# commands (proto), and both (protohelp).
RUN build() { name=$1; shift; rm -rf /b && cp -a /src /b && for p in "$@"; do git -C /b apply "$p"; done \
      && (cd /b && CGO_ENABLED=0 go build -trimpath -ldflags "-s -w -X github.com/roamer7038/wikictl/internal/cli.version=${WIKICTL_REF}-$name" -o "/out/$name/wikictl" ./cmd/wikictl); } \
 && build help /tmp/help.patch && build proto /tmp/wikictl.patch && build protohelp /tmp/wikictl.patch /tmp/help.patch

FROM ubuntu:24.04
ARG CLAUDE_VERSION=2.1.273
ARG WIKICTL_REF=v0.4.1
ARG PLUGIN_REF=b5763e8
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8
RUN apt-get update -q && apt-get install -qy --no-install-recommends \
      ca-certificates curl git ripgrep jq python3 python3-yaml python3-venv procps less file tree \
 && rm -rf /var/lib/apt/lists/*
# Ubuntu's image has a user with uid 1000; rename it so that files match the host user.
RUN usermod -l agent -d /home/agent -m ubuntu && groupmod -n agent ubuntu
# wikictl: the release binary, verified against its checksum, and the prototype.
RUN base=https://github.com/roamer7038/wikictl/releases/download/$WIKICTL_REF \
 && asset=wikictl_linux_$(uname -m) && cd /tmp \
 && curl -fsSL -o checksums.txt "$base/checksums.txt" && curl -fsSL -o "$asset" "$base/$asset" \
 && grep " $asset\$" checksums.txt | sha256sum -c --quiet - \
 && install -D -m 755 "$asset" /opt/wikictl/release/wikictl && rm -f "$asset" checksums.txt
COPY --from=wikictl-proto /out/ /opt/wikictl/
RUN git clone -q https://github.com/roamer7038/wikictl-claude-plugin.git /opt/plugin/base \
 && git -C /opt/plugin/base -c advice.detachedHead=false checkout -q "$PLUGIN_REF" && rm -rf /opt/plugin/base/.git
# Each directory of plugins/ is a variant: the base plugin with its files laid over it.
COPY plugins /opt/plugin-overlays
RUN for v in /opt/plugin-overlays/*/; do n=$(basename "$v"); cp -a /opt/plugin/base "/opt/plugin/$n"; cp -a "$v". "/opt/plugin/$n/"; done
# Commands the prototype conditions add to PATH, with the embedding model of
# wikictl-search downloaded at build time.
COPY ext /opt/eval-ext
RUN python3 -m venv /opt/eval-ext/venv \
 && /opt/eval-ext/venv/bin/pip install -q --no-cache-dir fastembed==0.7.1 numpy \
 && /opt/eval-ext/venv/bin/python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/opt/eval-ext/models')" \
 && chmod -R a+rX /opt/eval-ext
# Claude Code at a fixed version, installed for the agent user.
USER agent
RUN curl -fsSL https://claude.ai/install.sh | bash -s "$CLAUDE_VERSION" \
 && /home/agent/.local/bin/claude --version
USER root
RUN install -m 755 "$(readlink -f /home/agent/.local/bin/claude)" /usr/local/bin/claude && rm -rf /home/agent/.local /home/agent/.claude*
USER agent
WORKDIR /workspace
