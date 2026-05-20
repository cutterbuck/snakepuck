import dash_bootstrap_components as dbc
from dash import html


def create_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("MacNaughton HALO Project", href="/about"),
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavItem(dbc.NavLink("Team Standings", href="/team-standings", active="exact")),
                            dbc.NavItem(dbc.NavLink("Player Stats", href="/player-stats", active="exact")),
                            dbc.NavItem(
                                dbc.NavLink("Sample Raw Data", href="/sample-data", active="exact")
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    "Blog Posts",
                                    href="/blog-posts",
                                    active="partial",
                                )
                            ),
                            dbc.NavItem(dbc.NavLink("About", href="/about", active="exact")),
                        ],
                        navbar=True,
                    ),
                    id="navbar-collapse",
                    is_open=False,
                    navbar=True,
                ),
            ],
            fluid=True,
            style={"padding": "0 4%"},
        ),
        color=None,
        dark=True,
        style={"backgroundColor": "#0d2137"},
        className="mb-4",
    )
