import dash_bootstrap_components as dbc
from dash import dcc, html


def _section_card(title, content_md):
    return dbc.Card(
        dbc.CardBody(
            [
                html.H4(title, className="about-section-title"),
                dcc.Markdown(content_md, className="about-section-body", link_target="_blank"),
            ]
        ),
        className="about-card mb-4",
    )


def create_about_layout():
    return dbc.Container(
        [
            # Hero section
            html.Div(
                [
                    html.H1("The HALO Project", className="about-hero-title"),
                    html.P(
                        "Exploring AHL Player Tracking Data",
                        className="about-hero-subtitle",
                    ),
                    html.Hr(className="about-hero-divider"),
                    html.P(
                        "This project digs into Teamworks and Sportlogiq AHL player "
                        "tracking data to surface insights that go beyond traditional "
                        "box-score statistics. From shift-level visualizations to "
                        "expected goal models built from raw event data, the goal is "
                        "to find meaningful signals for player evaluation and team "
                        "success.",
                        className="about-hero-intro",
                    ),
                ],
                className="about-hero",
            ),
            # Content sections
            _section_card(
                "What You Can Do Here",
                """\
This site lets you explore AHL player and team performance at a level of granularity \
you won't find on traditional stats sites:

- **Shift-by-shift breakdowns** — See how a player performed across every shift in a game, \
not just the final stat line.
- **Live rink visualizations** — Watch tracking and event data unfold play-by-play on an \
interactive hockey rink.
- **Expected goal analytics** — Go beyond goals and assists with xG models derived from \
raw event data, broken down by situation (5-on-5, power play, etc.).
- **Deep-dive blog posts** — Analytical write-ups that use this data to answer specific \
questions about player evaluation.

Start with [Team Standings](/team-standings) to pick a team, drill into a player, \
and follow the data all the way down to individual shifts. You can also jump straight \
to any player from the [Player Stats](/player-stats) page.""",
            ),
            _section_card(
                "The Data",
                """\
The dataset contains a 30-game sample for 1,172 AHL players across parquet files for \
players, games, stints, events, and tracking data. That adds up to:

- **480** games
- **1.8 million+** event rows
- **2.2 million+** stints
- **13.5 million+** tracking data rows

You can browse the raw data directly in the [Sample Raw Data](/sample-data) section.""",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("Get in Touch", className="about-section-title"),
                        html.P(
                            "Have questions, feedback, or ideas for new analyses? "
                            "I'd love to hear from you.",
                            className="about-section-body",
                        ),
                        html.Ul(
                            [
                                html.Li(
                                    [
                                        "Email: ",
                                        html.A(
                                            "jakemacnaughton@gmail.com",
                                            href="mailto:jakemacnaughton@gmail.com",
                                            className="about-contact-link",
                                        ),
                                    ]
                                ),
                                html.Li(
                                    [
                                        "LinkedIn: ",
                                        html.A(
                                            "linkedin.com/in/jakemacnaughton",
                                            href="https://www.linkedin.com/in/jakemacnaughton/",
                                            target="_blank",
                                            rel="noopener noreferrer",
                                            className="about-contact-link",
                                        ),
                                    ]
                                ),
                            ],
                            className="about-contact-list",
                        ),
                    ]
                ),
                className="about-card mb-4",
            ),
        ],
        fluid=True,
        className="about-container",
    )
