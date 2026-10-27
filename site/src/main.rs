//! SnakePuck API: serves the dbt marts as JSON.
//!
//! Environment:
//!   DATA_DIR  serving files from infra/export_serving.py (default: data/serving)
//!   PORT      listen port (default: 8080; Cloud Run sets it)
//!
//! Local run, from site/ (data/ is git-ignored; the data is licensed):
//!   gcloud storage rsync -r gs://snakepuck-data/serving/dev data/serving
//!   cargo run

mod api;
mod data;

use std::path::PathBuf;
use std::time::Instant;

use anyhow::Result;
use tower_http::compression::CompressionLayer;
use tower_http::trace::TraceLayer;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| "info,tower_http=info".into()),
        )
        .init();

    let data_dir =
        PathBuf::from(std::env::var("DATA_DIR").unwrap_or_else(|_| "data/serving".into()));
    let started = Instant::now();
    let store = data::Store::load(&data_dir)?;
    tracing::info!(
        teams = store.teams.len(),
        seasons = store.seasons.len(),
        elapsed_ms = started.elapsed().as_millis() as u64,
        "loaded marts from {}",
        data_dir.display()
    );

    let app = api::router(store)
        .layer(CompressionLayer::new())
        .layer(TraceLayer::new_for_http());

    let port = std::env::var("PORT").unwrap_or_else(|_| "8080".into());
    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{port}")).await?;
    tracing::info!("listening on {}", listener.local_addr()?);
    axum::serve(listener, app).await?;
    Ok(())
}
