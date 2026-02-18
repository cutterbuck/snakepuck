import dash_bootstrap_components as dbc
from dash import html


def create_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("MacNaughton HALO Project", href="/"),
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Standings", href="/")),
                        dbc.NavItem(
                            dbc.NavLink("Player Analysis", href="/player-analysis")
                        ),
                        dbc.NavItem(
                            dbc.NavLink("Sample Raw Data", href="/sample-data")
                        ),
                        dbc.NavItem(dbc.NavLink("Blog Posts", href="/blog-posts")),
                        dbc.NavItem(
                            dbc.NavLink(
                                "Logout", href="/auth/logout", external_link=True
                            )
                        ),
                    ],
                    navbar=True,
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        className="mb-4",
    )
