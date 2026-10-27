# The API image: build in a Rust image, run the binary alone on distroless.
# Data isn't baked in; Cloud Run mounts the GCS bucket and DATA_DIR points into it.

FROM rust:1.99-slim-trixie AS build
WORKDIR /src

# Build dependencies first, against a stub main, so they're cached until Cargo.* change.
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo 'fn main() {}' > src/main.rs \
    && cargo build --release --locked \
    && rm -rf src

COPY src src
RUN touch src/main.rs && cargo build --release --locked

FROM gcr.io/distroless/cc-debian13:nonroot
COPY --from=build /src/target/release/snakepuck /snakepuck
ENV DATA_DIR=/data/serving/prod
EXPOSE 8080
ENTRYPOINT ["/snakepuck"]
