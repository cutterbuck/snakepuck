//! SnakePuck: the site's pages (Leptos) and its JSON API, in one crate.
//!
//! The server build (`ssr`) renders pages and serves the API; the browser build
//! (`hydrate`) compiles the same pages to WASM and makes the server-rendered HTML
//! interactive. HALO data lives only in `server`, which the browser build leaves out.

pub mod app;
#[cfg(feature = "ssr")]
pub mod server;
pub mod types;

/// Browser entry point: attach to the server-rendered page.
#[cfg(feature = "hydrate")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn hydrate() {
    console_error_panic_hook::set_once();
    leptos::mount::hydrate_body(app::App);
}
