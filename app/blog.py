"""Blog posts stored as Markdown files with YAML front matter.

Each post is ``content/blog/<slug>.md``:

    ---
    title: Post title
    date: 2026-05-21
    summary: One-line summary for the listing page
    draft: true          # optional; drafts are hidden unless SHOW_DRAFTS=1
    ---

    Markdown body...
"""

import datetime
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content" / "blog"


@dataclass(frozen=True)
class Post:
    slug: str
    title: str
    date: datetime.date | None
    summary: str | None
    content: str
    draft: bool


def show_drafts():
    return os.environ.get("SHOW_DRAFTS") == "1"


def parse_post(path):
    """Parse one Markdown file into a Post; raise ValueError if malformed."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name}: missing front matter")
    front, sep, body = text[4:].partition("\n---\n")
    if not sep:
        raise ValueError(f"{path.name}: unterminated front matter")
    meta = yaml.safe_load(front) or {}

    draft = bool(meta.get("draft", False))
    date = meta.get("date")
    if not meta.get("title"):
        raise ValueError(f"{path.name}: missing title")
    if date is not None and not isinstance(date, datetime.date):
        raise ValueError(f"{path.name}: date must be YYYY-MM-DD")
    if date is None and not draft:
        raise ValueError(f"{path.name}: published posts need a date")

    return Post(
        slug=path.stem,
        title=meta["title"],
        date=date,
        summary=meta.get("summary"),
        content=body.strip(),
        draft=draft,
    )


def load_posts(content_dir=CONTENT_DIR, include_drafts=None):
    """All posts, newest first. Drafts are included only when requested."""
    if include_drafts is None:
        include_drafts = show_drafts()
    posts = [parse_post(p) for p in sorted(Path(content_dir).glob("*.md"))]
    if not include_drafts:
        posts = [p for p in posts if not p.draft]
    # Undated drafts sort first, then newest published
    return sorted(posts, key=lambda p: p.date or datetime.date.max, reverse=True)


def get_post(slug, content_dir=CONTENT_DIR, include_drafts=None):
    """Look up a post by slug among loaded posts (never builds a path from input)."""
    return next(
        (p for p in load_posts(content_dir, include_drafts) if p.slug == slug), None
    )
