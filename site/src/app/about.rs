//! About: what the project is and what's in the data. Static.

use leptos::prelude::*;
use leptos_meta::Title;

#[component]
pub fn About() -> impl IntoView {
    view! {
        <Title text="HALO Project - About" />
        <div class="container-fluid about-container">
            <div class="about-hero">
                <h1 class="about-hero-title">"The HALO Project"</h1>
                <p class="about-hero-subtitle">"Exploring AHL Player Tracking Data"</p>
                <hr class="about-hero-divider" />
                <p class="about-hero-intro">
                    "This project digs into Teamworks and Sportlogiq AHL player tracking data to "
                    "surface insights that go beyond traditional box-score statistics. From "
                    "shift-level visualizations to expected goal models built from raw event "
                    "data, the goal is to find meaningful signals for player evaluation and "
                    "team success."
                </p>
            </div>

            <Section title="What You Can Do Here">
                <p>
                    "This site lets you explore AHL player and team performance at a level of "
                    "granularity you won't find on traditional stats sites:"
                </p>
                <ul>
                    <li>
                        <strong>"Shift-by-shift breakdowns"</strong>
                        " — See how a player performed across every shift in a game, not just "
                        "the final stat line."
                    </li>
                    <li>
                        <strong>"Live rink visualizations"</strong>
                        " — Watch tracking and event data unfold play-by-play on an interactive "
                        "hockey rink."
                    </li>
                    <li>
                        <strong>"Expected goal analytics"</strong>
                        " — Go beyond goals and assists with xG models derived from raw event "
                        "data, broken down by situation (5-on-5, power play, etc.)."
                    </li>
                    <li>
                        <strong>"Deep-dive blog posts"</strong>
                        " — Analytical write-ups that use this data to answer specific questions "
                        "about player evaluation."
                    </li>
                </ul>
                <p>
                    "Start with " <a href="/team-standings">"Team Standings"</a>
                    " to pick a team, drill into a player, and follow the data all the way down "
                    "to individual shifts. You can also jump straight to any player from the "
                    <a href="/player-stats">"Player Stats"</a> " page."
                </p>
            </Section>

            <Section title="The Data">
                <p>
                    "The dataset contains a 30-game sample for 1,172 AHL players across parquet "
                    "files for players, games, stints, events, and tracking data. That adds up to:"
                </p>
                <ul>
                    <li><strong>"480"</strong> " games"</li>
                    <li><strong>"1.8 million+"</strong> " event rows"</li>
                    <li><strong>"2.2 million+"</strong> " stints"</li>
                    <li><strong>"13.5 million+"</strong> " tracking data rows"</li>
                </ul>
                <p>
                    "You can browse the raw data directly in the "
                    <a href="/sample-data">"Sample Raw Data"</a> " section."
                </p>
            </Section>

            <div class="card about-card mb-4">
                <div class="card-body">
                    <h4 class="about-section-title">"Get in Touch"</h4>
                    <p class="about-section-body">
                        "Have questions, feedback, or ideas for new analyses? I'd love to hear "
                        "from you."
                    </p>
                    <ul class="about-contact-list">
                        <li>
                            "Email: "
                            <a href="mailto:jakemacnaughton@gmail.com" class="about-contact-link">
                                "jakemacnaughton@gmail.com"
                            </a>
                        </li>
                        <li>
                            "LinkedIn: "
                            <a
                                href="https://www.linkedin.com/in/jakemacnaughton/"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="about-contact-link"
                            >
                                "linkedin.com/in/jakemacnaughton"
                            </a>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    }
}

#[component]
fn Section(title: &'static str, children: Children) -> impl IntoView {
    view! {
        <div class="card about-card mb-4">
            <div class="card-body">
                <h4 class="about-section-title">{title}</h4>
                <div class="about-section-body">{children()}</div>
            </div>
        </div>
    }
}
