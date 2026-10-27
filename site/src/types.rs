//! Response types shared by the server (which builds them) and the browser (which
//! receives them from `/api/...`). One definition per response shape.

use serde::{Deserialize, Serialize};

/// Why a page's data couldn't be loaded.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum PageError {
    NotFound(String),
    Failed(String),
}

impl std::fmt::Display for PageError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NotFound(m) | Self::Failed(m) => f.write_str(m),
        }
    }
}

/// A blog post as the listing shows it.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PostSummary {
    pub slug: String,
    pub title: String,
    /// "May 21, 2026", "Undated", with " · DRAFT" for drafts.
    pub date_label: String,
    /// The post's summary, or the start of its text.
    pub excerpt: String,
}

/// A blog post, its body already rendered from Markdown.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Post {
    pub slug: String,
    pub title: String,
    pub date_label: String,
    pub html: String,
}
