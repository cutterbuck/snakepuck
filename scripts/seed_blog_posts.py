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
        "title": "The Consequences of Randomness in Hockey",
        "slug": "project-intro-dzone-puck-retrievals",
        "published_at": datetime(2026, 2, 19),
        "summary": (
            "Understanding randomness in hockey, and why process-driven "
            "metrics matter when evaluating team and player performance."
        ),
        "content": """\
## The Hockey Gods
Tonight the Montreal Canadiens will take on the Carolina Hurricanes in game one of the Easter Conference Final after barely surviving game seven in each of their first two series. Montreal, despite being outshot 29-9 and going nearly 27 minutes without registering a shot on goal, defeated Tampa Bay courtesy of Alex Newhook's goal at 11:07 of the 3rd period. They were outplayed by the Buffalo Sabres in their next game seven, albeit not as dramatically, yet won again courtesy of another timely Newhook goal. Does Montreal deserve to be playing in the ECF? Of course they do! Luck and randomness are part of hockey, and so far Montreal has had the Hockey Gods on their side. Can Montreal endure another two game sevens the same way to reclaim the Stanley Cup for Canada for the first time since 1993 when they last won it all? Statistics suggests it is possible but unlikely.

### Quantifying the Hockey Gods

Succeeding in any pursuit, whether it be winning the Stanley Cup, or scoring a perfect 1600 on the SATs, or winning the lottery, will require a certain degree of skill and a certain degree of luck. The statistical framework called [True Score Theory](https://conjointly.com/kb/true-score-theory/) provides a way to quantify just how much luck vs. how much skill may be involved in any of these endeavors. One would intuitively think that it takes more skill than luck to scores a perfect 1600 on the SATs. Likewise, one would think that winning the lottery is inherently lucky because even a child possesses enough skill to come up with a set of Powerball numbers. Consider the following formula:

> variance(observed outcome) = variance(skill) + (variance(luck)

We can look up the NHL standings on NHL to come up with one of the terms of this equation: the observed outcome.


In the book, [The Success Equation: Untangling Skill and Luck in Business, Sports, and Investing](https://www.amazon.com/Success-Equation-Untangling-Business-Investing/dp/1422184234), Mauboussin hashes out these ideas and applies them to the sports world. In this work, Mauboussin introduces a theoretical continuum ranging from 100% luck to 100% skill. He notes that success in domains such as chess is almost entirely attributable to skill, while outcomes in games like roulette are determined predominantly by luck. According to Mauboussin, hockey occupies a balanced position on this continuum, with approximately 53% of success attributed to luck.

![Luck-skill continuum](/assets/mauboussin_skill_vs_luck.jpg)

There are several rational explanations for this, particularly when considering a limited sample size such as a seven-game playoff series. Numerous factors can significantly influence the outcome, including an exceptionally performing opposing goaltender, unfavorable goalie interference reviews, or an unpredictable deflection off a linesman’s skate leading to a scoring opportunity. Hockey is inherently a dynamic sport characterized by considerable randomness. Upon examining some of the raw data, it becomes evident that much of what occurs during a game is attributable to chance. Even elite players typically participate for only around 20 minutes per game and may possess the puck for just 1-2% of total playtime.

### Reversion to the Mean
Activities that involve significant amounts of luck tend to show strong reversion to the mean. Mauboussin introduces a useful concept for quantifying this: the **shrinking factor**. The formula is straightforward:

> Expected result = average + shrinking factor x (observed result - average)

A shrinking factor of 1 means the activity is all skill — there is no reversion, and the observed result is the best predictor of future performance. A shrinking factor of 0 means the activity is all luck — the best prediction for the next outcome is simply the base rate.

To illustrate: in baseball, the shrinking factor for batting average is approximately 0.20. If a player is hitting .350 early in the season, the expected year-end average would be .265 + 0.20 x (.350 - .265) = **.282** — much closer to the league average than the hot start would suggest. The observed result tells us surprisingly little about the player’s true ability.

In hockey, where luck accounts for roughly 53% of observed outcomes, we should expect even more aggressive reversion. A player who posts exceptional plus-minus numbers over a 30-game stretch is far more likely to regress toward the mean than to sustain that pace. This doesn’t mean the player lacks skill — it means the metric is capturing a large amount of noise alongside the signal.

This is precisely why, in domains with high luck, it is more valuable to focus on the **underlying process** rather than the observed outcomes. Results like wins, losses, goals, assists, and points may deviate considerably from what would be expected over the long term. Process-driven metrics — like expected goals — attempt to measure the quality of chances created and allowed, stripping away some of the randomness that contaminates traditional stats.

### What Makes a Useful Statistic?
If most hockey statistics revert to the mean, which ones are actually worth paying attention to? Mauboussin proposes two criteria for evaluating any performance metric:

1. **Persistence (reliability)** — Does the statistic correlate with itself year over year? If a player ranks highly in a metric one season, do they tend to rank highly the next? High persistence suggests the metric is capturing something real and repeatable — skill rather than luck.

2. **Predictability (validity)** — Does the statistic correlate with the outcome you actually care about? A metric can be highly persistent but ultimately irrelevant if it doesn’t help predict wins, goals, or other meaningful results.

The most useful statistics score highly on **both** dimensions. In hockey, the year-over-year correlations are revealing:

- **Shots on goal per minute**: r = 0.89 — very persistent. A player’s shot generation rate is largely a function of skill, playing style, and deployment.
- **Shooting percentage**: r = 0.63 — moderately persistent. There is a skill component, but a meaningful portion of the variance is attributable to luck.
- **Plus-minus**: r = 0.32 — weakly persistent. This is a stat heavily influenced by teammates, opponents, goaltending, and random bounces. Its low reliability makes it a poor indicator of individual skill.

A key insight emerges: **the more a statistic depends on the interaction of teammates and opponents, the lower its year-over-year correlation tends to be.** Plus-minus is a team-dependent outcome masquerading as an individual stat. Shooting percentage depends on shot quality, goaltender performance, and deflections. Shots per minute, by contrast, is more directly within a player’s control.

This framework is what motivated the approach taken on this site. Rather than relying on traditional box-score statistics, I used event data to calculate each player’s on-ice expected goals for and against. Expected goal metrics attempt to isolate the quality of the process — the chances created and allowed — from the randomness of whether the puck happened to go in. For defensemen in particular, xG provides a more accurate reflection of on-ice performance than goals, assists, or plus-minus.

### The Paradox of Skill
There is one more idea from Mauboussin that is worth sitting with: as the overall level of skill in a league improves, **luck becomes a larger factor in determining outcomes**. This is counterintuitive but logical. Imagine plotting the distribution of skill across all NHL players. Over time, as training methods improve and talent identification gets better, the distribution shifts to the right (everyone is more skilled) but also **narrows** (the gap between the best and worst shrinks). Meanwhile, the distribution of luck remains unchanged.

When the skill gap between teams is razor-thin, the random elements — a bad bounce, a missed call, a hot goaltender — carry more weight in deciding who wins. This is why a seven-game playoff series can feel so unpredictable, and why the best regular-season team frequently fails to win the championship. It is not that skill doesn’t matter. It is that everyone is so skilled that luck tips the balance.

For analytics, this has a practical implication: the statistics we use need to be sensitive enough to detect small differences in skill amid a sea of noise. Blunt instruments like plus-minus or even raw goal totals are not up to the task. More granular, process-oriented metrics — expected goals, shot quality models, tracking-data-derived evaluations — offer a better chance of separating signal from noise.

A deeper analysis of defensemen’s D-zone loose puck recoveries and their effect on expected goals is coming in a future post.
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
