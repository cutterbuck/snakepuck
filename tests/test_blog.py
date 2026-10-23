"""Blog posts load from Markdown files; no database needed."""

import datetime
import json

import pytest

from app.blog import CONTENT_DIR, get_post, load_posts, parse_post

PUBLISHED_SLUG = "consequences-of-randomness-in-hockey"
DRAFT_SLUG = "dzone-lpr-analysis"


def _write(dir_, name, front, body="Body text"):
    path = dir_ / f"{name}.md"
    path.write_text(f"---\n{front}\n---\n\n{body}\n")
    return path


# ── Real content ────────────────────────────────────────────────────


def test_every_content_file_parses():
    for path in CONTENT_DIR.glob("*.md"):
        parse_post(path)


def test_published_post_loads():
    post = get_post(PUBLISHED_SLUG, include_drafts=False)
    assert post.title == "The Consequences of Randomness in Hockey"
    assert post.date == datetime.date(2026, 5, 21)
    assert post.content.startswith("#### Hockey Gods")


def test_draft_hidden_by_default(monkeypatch):
    monkeypatch.delenv("SHOW_DRAFTS", raising=False)
    assert DRAFT_SLUG not in [p.slug for p in load_posts()]
    assert get_post(DRAFT_SLUG) is None


def test_draft_visible_with_show_drafts(monkeypatch):
    monkeypatch.setenv("SHOW_DRAFTS", "1")
    assert get_post(DRAFT_SLUG).draft


# ── Parsing rules ───────────────────────────────────────────────────


def test_posts_sorted_newest_first(tmp_path):
    _write(tmp_path, "older", "title: Older\ndate: 2026-01-01")
    _write(tmp_path, "newer", "title: Newer\ndate: 2026-06-01")
    assert [p.slug for p in load_posts(tmp_path, include_drafts=False)] == [
        "newer",
        "older",
    ]


def test_undated_draft_allowed(tmp_path):
    _write(tmp_path, "wip", "title: WIP\ndraft: true")
    assert parse_post(tmp_path / "wip.md").date is None


@pytest.mark.parametrize(
    "front, error",
    [
        ("date: 2026-01-01", "missing title"),
        ("title: No date", "need a date"),
        ("title: Bad date\ndate: May 21", "YYYY-MM-DD"),
    ],
)
def test_invalid_front_matter_rejected(tmp_path, front, error):
    path = _write(tmp_path, "bad", front)
    with pytest.raises(ValueError, match=error):
        parse_post(path)


def test_missing_front_matter_rejected(tmp_path):
    path = tmp_path / "plain.md"
    path.write_text("# Just markdown\n")
    with pytest.raises(ValueError, match="missing front matter"):
        parse_post(path)


def test_slug_lookup_ignores_paths(tmp_path):
    _write(tmp_path, "post", "title: Post\ndate: 2026-01-01")
    assert get_post("../post", tmp_path, include_drafts=False) is None


# ── Pages ───────────────────────────────────────────────────────────


def test_listing_page(dash, monkeypatch):
    monkeypatch.delenv("SHOW_DRAFTS", raising=False)
    listing = json.dumps(
        dash.call(["blog-posts-list.children"], {"url.pathname": "/blog-posts"})
    )
    assert "The Consequences of Randomness in Hockey" in listing
    assert "working title" not in listing


def test_post_page(dash):
    post = json.dumps(
        dash.call(
            ["blog-post-content.children"], {"url.pathname": f"/blog/{PUBLISHED_SLUG}"}
        )
    )
    assert "Hockey Gods" in post
    assert "May 21, 2026" in post


def test_missing_post_page(dash):
    post = json.dumps(
        dash.call(["blog-post-content.children"], {"url.pathname": "/blog/nope"})
    )
    assert "Post not found" in post
