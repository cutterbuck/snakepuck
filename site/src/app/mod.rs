//! The site's pages: rendered on the server, then hydrated in the browser.

mod about;
mod blog;
mod fetch;
mod game_report;
mod layout;
mod player_analysis;
mod player_detail;
mod player_stats;
mod rink;
mod sample_data;
mod standings;
mod stats_table;
mod team_detail;

use leptos::prelude::*;
use leptos_meta::{Link, Meta, MetaTags, Stylesheet, provide_meta_context};
use leptos_router::components::{Route, Router, Routes};
use leptos_router::{SsrMode, path};

use about::About;
use blog::{BlogList, BlogPost};
use game_report::GameReportPage;
use layout::{Footer, Navbar, NotFound};
use player_analysis::PlayerAnalysisPage;
use player_detail::PlayerDetailPage;
use player_stats::PlayerStatsPage;
use sample_data::SampleDataPage;
use standings::StandingsPage;
use team_detail::TeamDetailPage;

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
                    // Pages with data render once it's loaded (SsrMode::Async), so the
                    // HTML is complete and a missing item gets a real 404.
                    <Route path=path!("/blog-posts") view=BlogList ssr=SsrMode::Async />
                    <Route path=path!("/blog/:slug") view=BlogPost ssr=SsrMode::Async />
                    <Route path=path!("/team-standings") view=StandingsPage ssr=SsrMode::Async />
                    <Route
                        path=path!("/player-analysis")
                        view=PlayerAnalysisPage
                        ssr=SsrMode::Async
                    />
                    <Route path=path!("/sample-data") view=SampleDataPage ssr=SsrMode::Async />
                    <Route path=path!("/player-stats") view=PlayerStatsPage ssr=SsrMode::Async />
                    // Stats tables link here; the Dash site's URLs use database ids.
                    <Route path=path!("/team/:team_abbr/:season") view=TeamDetailPage ssr=SsrMode::Async />
                    <Route path=path!("/player/:player_id") view=PlayerDetailPage ssr=SsrMode::Async />
                    <Route
                        path=path!("/player/:player_id/game/:game_id")
                        view=GameReportPage
                        ssr=SsrMode::Async
                    />
                </Routes>
            </main>
            <Footer />
        </Router>
    }
}
