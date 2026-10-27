# The site image: the server and the browser bundle, built by cargo-leptos, run alone on
# distroless. Built from the repo root (see /.dockerignore: only site/ and content/blog/
# are sent). Data isn't baked in: Cloud Run mounts the bucket and DATA_DIR points into it.

FROM rust:1.99-slim-trixie AS build
ARG CARGO_LEPTOS_VERSION=0.3.11
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && rustup target add wasm32-unknown-unknown

# cargo-leptos from its release binaries, checked against the published checksum.
RUN set -eux; \
    name="cargo-leptos-$(uname -m)-unknown-linux-gnu.tar.gz"; \
    base="https://github.com/leptos-rs/cargo-leptos/releases/download/v${CARGO_LEPTOS_VERSION}"; \
    cd /tmp; \
    curl -fsSLO "$base/$name"; \
    curl -fsSLO "$base/$name.sha256"; \
    echo "$(cut -d' ' -f1 "$name.sha256")  $name" | sha256sum -c -; \
    tar -xzf "$name"; \
    find /tmp -name cargo-leptos -type f -exec install -m 755 {} /usr/local/bin/ \; ; \
    rm -rf /tmp/cargo-leptos*; \
    cargo leptos --version

WORKDIR /src/site
COPY site/ ./
RUN cargo leptos build --release

FROM gcr.io/distroless/cc-debian13:nonroot
COPY --from=build /src/site/target/release/snakepuck /snakepuck
COPY --from=build /src/site/target/site /site
COPY content/blog /content/blog
ENV DATA_DIR=/data/serving/prod \
    CONTENT_DIR=/content/blog \
    LEPTOS_OUTPUT_NAME=snakepuck \
    LEPTOS_SITE_ROOT=/site \
    LEPTOS_SITE_PKG_DIR=pkg \
    LEPTOS_SITE_ADDR=0.0.0.0:8080 \
    LEPTOS_ENV=PROD
EXPOSE 8080
ENTRYPOINT ["/snakepuck"]
