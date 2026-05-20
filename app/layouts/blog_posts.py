import dash_bootstrap_components as dbc
from dash import html


def create_blog_posts_layout():
    return dbc.Container(
        [
            html.Div(
                [
                    html.H1("Blog Posts", className="blog-list-title"),
                    html.P(
                        "Analytical deep-dives into AHL player tracking data. Coming soon.",
                        className="blog-list-subtitle",
                    ),
                ],
                className="blog-list-header",
            ),
            html.Div(id="blog-posts-list"),
        ],
        fluid=True,
        className="blog-list-container",
    )
