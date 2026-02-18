import dash_bootstrap_components as dbc
from dash import html


def create_blog_posts_layout():
    return dbc.Container(
        [
            html.H2("Blog Posts", className="mb-4"),
            html.Div(id="blog-posts-list"),
        ],
        fluid=True,
        style={"maxWidth": "720px"},
    )
