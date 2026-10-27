//! The site's pages: rendered on the server, then hydrated in the browser.

mod about;
mod layout;

use leptos::prelude::*;
use leptos_meta::{Link, Meta, MetaTags, Stylesheet, provide_meta_context};
use leptos_router::components::{Route, Router, Routes};
use leptos_router::path;

use about::About;
use layout::{Footer, Navbar, NotFound, Unported};

/// The current (Dash) site, where pages not yet ported still live.
pub const OLD_SITE: &str = "https://snakepuck.com";

const DESCRIPTION: &str = "Exploring AHL player tracking data — shift-level visualizations, \
                           expected goal models, and deep-dive analytics.";

/// The HTML document around the app (server only).
pub fn shell(options: LeptosOptions) -> impl IntoView {
    view! {
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <link
                    rel="stylesheet"
                    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.6/dist/css/bootstrap.min.css"
                />
                <AutoReload options=options.clone() />
                <HydrationScripts options />
                <MetaTags />
            </head>
            <body>
                <App />
            </body>
        </html>
    }
}

#[component]
pub fn App() -> impl IntoView {
    provide_meta_context();
    view! {
        <Stylesheet id="leptos" href="/pkg/snakepuck.css" />
        <Link rel="icon" href="/favicon.ico" />
        <Meta property="og:title" content="MacNaughton HALO Project" />
        <Meta property="og:description" content=DESCRIPTION />
        <Meta property="og:type" content="website" />
        <Meta name="twitter:card" content="summary" />
        <Meta name="twitter:title" content="MacNaughton HALO Project" />
        <Meta name="twitter:description" content=DESCRIPTION />
        <Router>
            <Navbar />
            <main style="padding: 0 4%; min-height: calc(100vh - 160px)">
                <Routes fallback=NotFound>
                    <Route path=path!("/") view=About />
                    <Route path=path!("/about") view=About />
                    <Route
                        path=path!("/team-standings")
                        view=|| view! { <Unported title="Team Standings" old_path="/team-standings" /> }
                    />
                    <Route
                        path=path!("/player-stats")
                        view=|| view! { <Unported title="Player Stats" old_path="/player-stats" /> }
                    />
                    <Route
                        path=path!("/player-analysis")
                        view=|| view! { <Unported title="Player Analysis" old_path="/player-analysis" /> }
                    />
                    <Route
                        path=path!("/sample-data")
                        view=|| view! { <Unported title="Sample Raw Data" old_path="/sample-data" /> }
                    />
                    <Route
                        path=path!("/blog-posts")
                        view=|| view! { <Unported title="Blog Posts" old_path="/blog-posts" /> }
                    />
                </Routes>
            </main>
            <Footer />
        </Router>
    }
}
