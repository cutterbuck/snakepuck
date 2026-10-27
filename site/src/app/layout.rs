//! What every page shares: the navbar and footer, and error and not-found pages.

use leptos::prelude::*;
use leptos_meta::Title;
use leptos_router::hooks::use_location;

use crate::types::PageError;

const NAV: [(&str, &str); 5] = [
    ("Team Standings", "/team-standings"),
    ("Player Stats", "/player-stats"),
    ("Sample Raw Data", "/sample-data"),
    ("Blog Posts", "/blog-posts"),
    ("About", "/about"),
];

#[component]
pub fn Navbar() -> impl IntoView {
    let (open, set_open) = signal(false);
    let pathname = use_location().pathname;
    let is_active = move |href: &str| {
        let path = pathname.get();
        // Blog posts stay highlighted on a post's own page (/blog/<slug>).
        path == href || (href == "/blog-posts" && path.starts_with("/blog/"))
    };

    view! {
        <nav class="navbar navbar-expand-md navbar-dark mb-4" style="background-color: #0d2137">
            <div class="container-fluid" style="padding: 0 4%">
                <a class="navbar-brand" href="/about">
                    "MacNaughton HALO Project"
                </a>
                <button
                    class="navbar-toggler"
                    type="button"
                    aria-label="Toggle navigation"
                    on:click=move |_| set_open.update(|o| *o = !*o)
                >
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" class:show=open>
                    <ul class="navbar-nav">
                        {NAV
                            .into_iter()
                            .map(|(label, href)| {
                                view! {
                                    <li class="nav-item">
                                        <a
                                            class="nav-link"
                                            class:active=move || is_active(href)
                                            href=href
                                            on:click=move |_| set_open.set(false)
                                        >
                                            {label}
                                        </a>
                                    </li>
                                }
                            })
                            .collect_view()}
                    </ul>
                </div>
            </div>
        </nav>
    }
}

#[component]
pub fn Footer() -> impl IntoView {
    view! {
        <footer class="site-footer">
            <div class="container-fluid text-center">
                <span class="footer-name">"Jake MacNaughton"</span>
                <span class="footer-sep">" · "</span>
                <a href="mailto:jakemacnaughton@gmail.com" class="footer-link">
                    "jakemacnaughton@gmail.com"
                </a>
                <span class="footer-sep">" · "</span>
                <a
                    href="https://www.linkedin.com/in/jakemacnaughton/"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="footer-link"
                >
                    "LinkedIn"
                </a>
            </div>
        </footer>
    }
}

/// Shown when a page's data couldn't be loaded. Sets the HTTP status when server
/// rendering (pages with data render in SsrMode::Async, so the status isn't sent yet).
#[component]
pub fn PageMessage(error: PageError) -> impl IntoView {
    #[cfg(feature = "ssr")]
    if let Some(response) = use_context::<leptos_axum::ResponseOptions>() {
        response.set_status(match error {
            PageError::NotFound(_) => axum::http::StatusCode::NOT_FOUND,
            PageError::Failed(_) => axum::http::StatusCode::INTERNAL_SERVER_ERROR,
        });
    }
    let (title, detail) = match error {
        PageError::NotFound(m) => ("Not found", m),
        PageError::Failed(m) => ("Something went wrong", m),
    };
    view! {
        <div class="about-container">
            <h3>{title}</h3>
            <p class="text-muted">{detail}</p>
        </div>
    }
}

/// Click handler for a table row that opens `href`. Clicks on a link inside the row
/// are left to the link.
pub fn row_link(href: String) -> impl Fn(leptos::ev::MouseEvent) + 'static {
    use leptos::wasm_bindgen::JsCast;
    let navigate = leptos_router::hooks::use_navigate();
    move |ev| {
        let target = ev
            .target()
            .and_then(|t| t.dyn_into::<leptos::web_sys::Element>().ok());
        let on_link = target.is_some_and(|t| t.closest("a").ok().flatten().is_some());
        if !on_link {
            navigate(&href, Default::default());
        }
    }
}

#[component]
pub fn NotFound() -> impl IntoView {
    #[cfg(feature = "ssr")]
    if let Some(response) = use_context::<leptos_axum::ResponseOptions>() {
        response.set_status(axum::http::StatusCode::NOT_FOUND);
    }
    view! {
        <Title text="HALO Project - Not Found" />
        <div class="about-container">
            <h2>"Page not found"</h2>
            <p class="text-muted">
                "Try the " <a href="/about">"About"</a> " page or "
                <a href="/team-standings">"Team Standings"</a> "."
            </p>
        </div>
    }
}
