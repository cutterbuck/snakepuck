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
        "title": "Macro-level Thoughts",
        "slug": "project-intro-dzone-puck-retrievals",
        "published_at": datetime(2026, 2, 19),
        "summary": (
            "The consequences of randomness in hockey, and why process-driven "
            "metrics matter when evaluating team and player performance."
        ),
        "content": """\
## The Consequences of Randomness in Hockey
My perspective on hockey analytics is significantly shaped by Michael Mauboussin’s book, [The Success Equation: Untangling Skill and Luck in Business, Sports, and Investing](https://www.amazon.com/Success-Equation-Untangling-Business-Investing/dp/1422184234). In this work, Mauboussin introduces a theoretical continuum ranging from 100% luck to 100% skill. He notes that success in domains such as chess is almost entirely attributable to skill, while outcomes in games like roulette are determined predominantly by luck. According to Mauboussin, hockey occupies a balanced position on this continuum, with approximately 53% of success attributed to luck.

![Luck-skill continuum](/assets/mauboussin_skill_vs_luck.jpg)

There are several rational explanations for this, particularly when considering a limited sample size such as a seven-game playoff series. Numerous factors can significantly influence the outcome, including an exceptionally performing opposing goaltender, unfavorable goalie interference reviews, or an unpredictable deflection off a linesman’s skate leading to a scoring opportunity. Hockey is inherently a dynamic sport characterized by considerable randomness. Upon examining some of the raw data, it becomes evident that much of what occurs during a game is attributable to chance. Even elite players typically participate for only around 20 minutes per game and may possess the puck for just 1-2% of total playtime.

Activities that involve significant amounts of luck tend to show strong mean reversion. In hockey, it’s more valuable to focus on the underlying process rather than just the observed outcomes, since results like wins, losses, goals, assists, and points may deviate considerably from what would be expected over the long term. Therefore, I used event data to calculate each player’s on-ice expected goals for and against. Expected goal metrics for defensemen provide a more accurate reflection of their performance on the ice compared to traditional stats like goals, assists, or plus-minus ratings.

A deeper analysis of defensemen’s D-zone loose puck recoveries and their effect on expected goals is coming soon.
""",
    },
]


def main():
    app = create_app()
    with app.app_context():
        for post_data in POSTS:
            existing = BlogPost.query.filter_by(slug=post_data["slug"]).first()
            if existing:
                existing.title = post_data["title"]
                existing.summary = post_data.get("summary")
                existing.content = post_data["content"]
                existing.published_at = post_data["published_at"]
                print(f"Updated: {post_data['title']}")
            else:
                post = BlogPost(**post_data)
                db.session.add(post)
                print(f"Added: {post_data['title']}")
        db.session.commit()
        print("Done.")


if __name__ == "__main__":
    main()
