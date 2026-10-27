//! Blog Posts: the listing, and one post.

use leptos::prelude::*;
use leptos_meta::Title;
use leptos_router::hooks::use_params_map;

use super::fetch;
use super::layout::PageMessage;
use crate::types::PageError;

#[component]
pub fn BlogList() -> impl IntoView {
    let posts = Resource::new(|| (), |_| fetch::blog_posts());
    view! {
        <Title text="HALO Project - Blog Posts" />
        <div class="blog-list-container">
            <div class="blog-list-header">
                <h1 class="blog-list-title">"Blog Posts"</h1>
                <p class="blog-list-subtitle">
                    "Analytical deep-dives into AHL player tracking data"
                </p>
            </div>
            <Suspense fallback=|| ()>
                {move || Suspend::new(async move {
                    match posts.await {
                        Ok(posts) if posts.is_empty() => view! { <ComingSoon /> }.into_any(),
                        Ok(posts) => posts
                            .into_iter()
                            .map(|post| {
                                let href = format!("/blog/{}", post.slug);
                                view! {
                                    <div class="card blog-card">
                                        <div class="card-body">
                                            <div class="blog-card-date">{post.date_label}</div>
                                            <h3 class="blog-card-title">
                                                <a href=href.clone() class="blog-card-title-link">
                                                    {post.title}
                                                </a>
                                            </h3>
                                            <p class="blog-card-excerpt">{post.excerpt}</p>
                                            <a href=href class="blog-card-read-more">
                                                "Read more →"
                                            </a>
                                        </div>
                                    </div>
                                }
                            })
                            .collect_view()
                            .into_any(),
                        Err(e) => view! { <PageMessage error=e /> }.into_any(),
                    }
                })}
            </Suspense>
        </div>
    }
}

#[component]
fn ComingSoon() -> impl IntoView {
    view! {
        <div class="card blog-card">
            <div class="card-body">
                <h4 class="text-center mb-3">"Stay Tuned"</h4>
                <p class="text-center text-muted mb-0">
                    "Blog posts are on the way. Check back soon for analytical deep-dives into "
                    "AHL player tracking data."
                </p>
            </div>
        </div>
    }
}

#[component]
pub fn BlogPost() -> impl IntoView {
    let params = use_params_map();
    let post = Resource::new(
        move || params.read().get("slug").unwrap_or_default(),
        fetch::blog_post,
    );
    view! {
        <div class="blog-detail-container">
            <Suspense fallback=|| ()>
                {move || Suspend::new(async move {
                    match post.await {
                        Ok(post) => view! {
                            <Title text=format!("HALO Project - {}", post.title) />
                            <a href="/blog-posts" class="blog-detail-back">
                                "← Back to Blog Posts"
                            </a>
                            <div class="blog-detail-header">
                                <h1 class="blog-detail-title">{post.title}</h1>
                                <div class="blog-detail-date">{post.date_label}</div>
                            </div>
                            <div class="blog-detail-content">
                                <div class="blog-post-body" inner_html=post.html></div>
                            </div>
                        }
                        .into_any(),
                        Err(PageError::NotFound(_)) => view! {
                            <Title text="HALO Project - Blog Post" />
                            <PageMessage error=PageError::NotFound("Post not found".into()) />
                            <a href="/blog-posts">"Back to Blog Posts"</a>
                        }
                        .into_any(),
                        Err(e) => view! { <PageMessage error=e /> }.into_any(),
                    }
                })}
            </Suspense>
        </div>
    }
}
