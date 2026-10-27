//! Blog posts: `content/blog/<slug>.md`, Markdown with YAML front matter, loaded at
//! startup (the same files and rules the Dash site uses, in `app/blog.py`):
//!
//! ```text
//! ---
//! title: Post title
//! date: 2026-05-21
//! summary: One-line summary for the listing page
//! draft: true          # optional; drafts are hidden unless SHOW_DRAFTS=1
//! ---
//! Markdown body...
//! ```

use std::path::Path;

use anyhow::{Context, Result, bail};
use pulldown_cmark::{CowStr, Event, Options, Parser, Tag, TagEnd};
use serde::Deserialize;

use crate::types::{Post, PostSummary};

#[derive(Deserialize)]
struct FrontMatter {
    title: Option<String>,
    date: Option<String>,
    summary: Option<String>,
    #[serde(default)]
    draft: bool,
}

#[derive(Debug, Clone)]
struct Entry {
    slug: String,
    title: String,
    /// (year, month, day)
    date: Option<(u32, u32, u32)>,
    summary: Option<String>,
    markdown: String,
    draft: bool,
}

/// Every post, newest first (undated drafts before all of them).
#[derive(Default)]
pub struct Blog {
    entries: Vec<Entry>,
}

impl Blog {
    /// Load `<dir>/*.md`. Drafts are kept only if `include_drafts`.
    pub fn load(dir: &Path, include_drafts: bool) -> Result<Self> {
        let mut entries = Vec::new();
        for file in std::fs::read_dir(dir).with_context(|| format!("reading {}", dir.display()))? {
            let path = file?.path();
            if path.extension().is_some_and(|e| e == "md") {
                let text = std::fs::read_to_string(&path)?;
                let slug = path
                    .file_stem()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_string();
                entries.push(parse(&slug, &text).with_context(|| format!("{}", path.display()))?);
            }
        }
        entries.retain(|e| include_drafts || !e.draft);
        entries.sort_by_key(|e| std::cmp::Reverse(e.date.unwrap_or((u32::MAX, 0, 0))));
        Ok(Self { entries })
    }

    pub fn list(&self) -> Vec<PostSummary> {
        self.entries
            .iter()
            .map(|e| PostSummary {
                slug: e.slug.clone(),
                title: e.title.clone(),
                date_label: date_label(e),
                excerpt: e.summary.clone().unwrap_or_else(|| {
                    let start: String = e.markdown.chars().take(200).collect();
                    format!("{start}...")
                }),
            })
            .collect()
    }

    /// Looks the slug up among loaded posts; it's never used to build a path.
    pub fn get(&self, slug: &str) -> Option<Post> {
        self.entries.iter().find(|e| e.slug == slug).map(|e| Post {
            slug: e.slug.clone(),
            title: e.title.clone(),
            date_label: date_label(e),
            html: render(&e.markdown),
        })
    }
}

fn parse(slug: &str, text: &str) -> Result<Entry> {
    let Some(rest) = text.strip_prefix("---\n") else {
        bail!("missing front matter")
    };
    let Some((front, body)) = rest.split_once("\n---\n") else {
        bail!("unterminated front matter")
    };
    let meta: FrontMatter = serde_yaml_ng::from_str(front)?;
    let Some(title) = meta.title.filter(|t| !t.is_empty()) else {
        bail!("missing title")
    };
    let date = match meta.date.as_deref() {
        None => None,
        Some(d) => Some(parse_date(d).with_context(|| format!("date {d:?} must be YYYY-MM-DD"))?),
    };
    if date.is_none() && !meta.draft {
        bail!("published posts need a date");
    }
    Ok(Entry {
        slug: slug.to_string(),
        title,
        date,
        summary: meta.summary,
        markdown: body.trim().to_string(),
        draft: meta.draft,
    })
}

fn parse_date(d: &str) -> Option<(u32, u32, u32)> {
    let mut parts = d.split('-').map(|p| p.parse::<u32>().ok());
    let (y, m, day) = (parts.next()??, parts.next()??, parts.next()??);
    (parts.next().is_none() && (1..=12).contains(&m) && (1..=31).contains(&day))
        .then_some((y, m, day))
}

const MONTHS: [&str; 12] = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];

fn date_label(e: &Entry) -> String {
    let date = e.date.map_or("Undated".to_string(), |(y, m, d)| {
        format!("{} {d}, {y}", MONTHS[m as usize - 1])
    });
    if e.draft {
        format!("{date} · DRAFT")
    } else {
        date
    }
}

/// Markdown to HTML, with links opening in a new tab (as on the Dash site).
fn render(markdown: &str) -> String {
    let options = Options::ENABLE_TABLES | Options::ENABLE_STRIKETHROUGH;
    let events = Parser::new_ext(markdown, options).map(|event| match event {
        Event::Start(Tag::Link {
            dest_url, title, ..
        }) => {
            let title = match title.is_empty() {
                true => String::new(),
                false => format!(" title=\"{}\"", escape_attr(&title)),
            };
            Event::Html(CowStr::from(format!(
                "<a href=\"{}\"{title} target=\"_blank\" rel=\"noopener noreferrer\">",
                escape_attr(&dest_url)
            )))
        }
        Event::End(TagEnd::Link) => Event::Html(CowStr::from("</a>")),
        other => other,
    });
    let mut html = String::new();
    pulldown_cmark::html::push_html(&mut html, events);
    html
}

fn escape_attr(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('"', "&quot;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Load `files` from a fresh temp dir (one per call: tests run in parallel).
    fn blog(files: &[(&str, &str)], include_drafts: bool) -> Result<Blog> {
        static CALLS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
        let call = CALLS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let dir =
            std::env::temp_dir().join(format!("snakepuck-blog-{}-{call}", std::process::id()));
        std::fs::create_dir_all(&dir)?;
        for (name, text) in files {
            std::fs::write(dir.join(name), text)?;
        }
        let blog = Blog::load(&dir, include_drafts);
        std::fs::remove_dir_all(&dir)?;
        blog
    }

    const OLD: &str =
        "---\ntitle: Old\ndate: 2025-01-02\n---\nSee [the site](https://x.y/?a=1&b=2).";
    const NEW: &str = "---\ntitle: \"New: a post\"\ndate: 2026-05-21\nsummary: Short.\n---\n# Hi\n";
    const DRAFT: &str = "---\ntitle: Draft\ndraft: true\n---\nWork in progress";

    #[test]
    fn newest_first_drafts_hidden_by_default() {
        let b = blog(
            &[("old.md", OLD), ("new.md", NEW), ("draft.md", DRAFT)],
            false,
        )
        .unwrap();
        let list = b.list();
        let slugs: Vec<_> = list.iter().map(|p| p.slug.as_str()).collect();
        assert_eq!(slugs, ["new", "old"]);
        assert_eq!(list[0].title, "New: a post");
        assert_eq!(list[0].date_label, "May 21, 2026");
        assert_eq!(list[0].excerpt, "Short.");
        assert!(list[1].excerpt.ends_with("..."));
        assert!(b.get("draft").is_none());
    }

    #[test]
    fn drafts_shown_when_asked_undated_first() {
        let b = blog(&[("old.md", OLD), ("draft.md", DRAFT)], true).unwrap();
        assert_eq!(b.list()[0].date_label, "Undated · DRAFT");
    }

    #[test]
    fn links_open_in_a_new_tab_and_are_escaped() {
        let b = blog(&[("old.md", OLD)], false).unwrap();
        let html = b.get("old").unwrap().html;
        assert!(
            html.contains(r#"<a href="https://x.y/?a=1&amp;b=2" target="_blank" rel="noopener noreferrer">the site</a>"#),
            "{html}"
        );
    }

    #[test]
    fn rejects_malformed_posts() {
        for (text, why) in [
            ("no front matter", "missing front matter"),
            ("---\ndate: 2026-01-01\n---\nx", "missing title"),
            ("---\ntitle: T\n---\nx", "published posts need a date"),
            ("---\ntitle: T\ndate: 21/05/2026\n---\nx", "YYYY-MM-DD"),
        ] {
            let err = format!("{:#}", blog(&[("bad.md", text)], false).err().unwrap());
            assert!(err.contains(why), "{err}");
        }
    }
}
