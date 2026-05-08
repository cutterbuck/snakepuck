import dash_bootstrap_components as dbc
from dash import html


def create_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("MacNaughton HALO Project", href="/"),
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Team Standings", href="/", active="exact")),
                        dbc.NavItem(dbc.NavLink("Player Stats", href="/player-stats", active="exact")),
                        # dbc.NavItem(
                        #     dbc.NavLink("Player Analysis", href="/player-analysis", active="exact")
                        # ),
                        dbc.NavItem(
                            dbc.NavLink("Sample Raw Data", href="/sample-data", active="exact")
                        ),
                        dbc.NavItem(dbc.NavLink("Blog Posts", href="/blog-posts", active="partial")),
                        # AUTH DISABLED — uncomment to re-enable logout
                        # dbc.NavItem(
                        #     dbc.NavLink(
                        #         "Logout", href="/auth/logout", external_link=True
                        #     )
                        # ),
                    ],
                    navbar=True,
                ),
            ],
            fluid=True,
        ),
        color=None,
        dark=True,
        style={"backgroundColor": "#0d2137"},
        className="mb-4",
    )
