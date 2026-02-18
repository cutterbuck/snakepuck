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
            return html.P("No blog posts yet.", className="text-muted")

        items = []
        for post in posts:
            items.append(
                html.Div(
                    [
                        html.A(
                            post.title,
                            href=f"/blog/{post.slug}",
                            className="blog-post-link",
                        ),
                        html.Div(
                            post.published_at.strftime("%B %-d, %Y"),
                            className="blog-post-date",
                        ),
                    ],
                    className="blog-post-item",
                )
            )

        return items

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
                    "← Back to Blog Posts",
                    href="/blog-posts",
                    className="blog-post-back",
                ),
                html.H2(post.title, className="mt-3 mb-1"),
                html.Div(
                    post.published_at.strftime("%B %-d, %Y"),
                    className="blog-post-date mb-4",
                ),
                dcc.Markdown(post.content, className="blog-post-body"),
            ]
        )
