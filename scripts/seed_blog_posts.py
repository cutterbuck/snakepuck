"""Seed blog posts.

Usage:
    python -m scripts.seed_blog_posts
"""

from datetime import datetime

from app import create_app
from app.extensions import db
from app.models.blog_post import BlogPost

POSTS = [
    {
        "title": "Project Intro; Defensemen Puck Retrievals",
        "slug": "project-intro-defensemen-puck-retrievals",
        "published_at": datetime(2026, 2, 19),
        "content": """\
## Introduction

Welcome to the MacNaughton HALO Project. This is the first in a series of blog posts where we'll explore hockey analytics through the lens of player tracking data, expected goals models, and situational analysis.

The goal of this project is to surface insights that go beyond traditional box-score statistics — examining *how* and *where* players contribute, not just the final tallies.

---

## Defensemen Puck Retrievals

One of the most undervalued aspects of a defenseman's game is their ability to retrieve loose pucks efficiently. Whether it's a dump-in along the boards, a puck rimmed around the end wall, or a battle behind the net, puck retrievals set the tone for controlled zone exits and transition play.

### Why It Matters

A defenseman who consistently wins puck battles and retrieves dump-ins gives their team a significant advantage:

- **Controlled breakouts** — Retrieving the puck cleanly leads to tape-to-tape passes out of the zone rather than desperation clears.
- **Time on attack** — Efficient retrievals reduce the time spent hemmed in the defensive zone.
- **Transition offense** — The best retrievers turn defense into offense in a single play.

### What We're Measuring

Using player tracking data, we can look at:

1. **Retrieval success rate** — How often does the defenseman come away with possession after contesting a loose puck?
2. **Time to retrieval** — How quickly does the defenseman get to the puck after a dump-in?
3. **Exit quality** — After retrieving the puck, does the play result in a controlled zone exit, a clear, or a turnover?

### Early Observations

Our initial analysis suggests that retrieval ability varies significantly across defensemen, even among those with similar ice time and defensive zone start rates. Some defensemen are consistently faster to the puck and more reliable in transitioning play up ice.

We'll be diving deeper into specific player comparisons and visualizations in upcoming posts.

---

*Stay tuned for more analysis. Next up, we'll look at how retrieval efficiency correlates with on-ice expected goals against.*
""",
    },
]


def main():
    app = create_app()
    with app.app_context():
        for post_data in POSTS:
            existing = BlogPost.query.filter_by(slug=post_data["slug"]).first()
            if existing:
                print(f"Post already exists: {post_data['title']}")
                continue
            post = BlogPost(**post_data)
            db.session.add(post)
            print(f"Added: {post_data['title']}")
        db.session.commit()
        print("Done.")


if __name__ == "__main__":
    main()
