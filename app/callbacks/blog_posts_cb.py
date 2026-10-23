import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from app.models.blog_post import BlogPost


def register_blog_posts_callbacks(dash_app):
    # ── Listing page ────────────────────────────────────────────────
    @dash_app.callback(
        Output("blog-posts-list", "children"),
        Input("url", "pathname"),
    )
    def update_blog_posts_list(pathname):
        if pathname != "/blog-posts":
            from dash import no_update

            return no_update

        posts = BlogPost.query.order_by(BlogPost.published_at.desc()).all()

        if not posts:
            return dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("Stay Tuned", className="text-center mb-3"),
                        html.P(
                            "Blog posts are on the way. Check back soon for "
                            "analytical deep-dives into AHL player tracking data.",
                            className="text-center text-muted mb-0",
                        ),
                    ],
                ),
                className="blog-card",
            )

        cards = []
        for post in posts:
            excerpt = post.summary or (post.content[:200] + "...")
            cards.append(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(
                                post.published_at.strftime("%B %-d, %Y"),
                                className="blog-card-date",
                            ),
                            html.H3(
                                html.A(
                                    post.title,
                                    href=f"/blog/{post.slug}",
                                    className="blog-card-title-link",
                                ),
                                className="blog-card-title",
                            ),
                            html.P(excerpt, className="blog-card-excerpt"),
                            html.A(
                                "Read more \u2192",
                                href=f"/blog/{post.slug}",
                                className="blog-card-read-more",
                            ),
                        ]
                    ),
                    className="blog-card",
                )
            )

        return cards

    # ── Detail page ─────────────────────────────────────────────────
    @dash_app.callback(
        Output("blog-post-content", "children"),
        Input("url", "pathname"),
    )
    def update_blog_post_detail(pathname):
        if not pathname or not pathname.startswith("/blog/"):
            from dash import no_update

            return no_update

        slug = pathname.split("/blog/", 1)[1]
        post = BlogPost.query.filter_by(slug=slug).first()

        if not post:
            return html.Div(
                [
                    html.H3("Post not found"),
                    html.A("Back to Blog Posts", href="/blog-posts"),
                ]
            )

        return html.Div(
            [
                html.A(
                    "\u2190 Back to Blog Posts",
                    href="/blog-posts",
                    className="blog-detail-back",
                ),
                html.Div(
                    [
                        html.H1(post.title, className="blog-detail-title"),
                        html.Div(
                            post.published_at.strftime("%B %-d, %Y"),
                            className="blog-detail-date",
                        ),
                    ],
                    className="blog-detail-header",
                ),
                html.Div(
                    dcc.Markdown(
                        post.content, className="blog-post-body", link_target="_blank"
                    ),
                    className="blog-detail-content",
                ),
            ]
        )
