import dash_bootstrap_components as dbc
from dash import html


def create_blog_post_detail_layout():
    return dbc.Container(
        [
            html.Div(id="blog-post-content"),
        ],
        fluid=True,
        className="blog-detail-container",
    )
