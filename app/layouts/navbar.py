import dash_bootstrap_components as dbc
from dash import html


def create_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("SnakePuck Analytics", href="/"),
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Standings", href="/")),
                        dbc.NavItem(dbc.NavLink("Games", href="/games")),
                        dbc.NavItem(dbc.NavLink("Players", href="/players")),
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
