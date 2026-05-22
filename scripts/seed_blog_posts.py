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
        "published_at": datetime(2026, 5, 21),
        "summary": (
            "Understanding randomness in hockey, and why process-driven "
            "metrics matter when evaluating team and player performance."
        ),
        "content": """\

#### Hockey Gods, Parlez Vous Francais?
Tonight the Montreal Canadiens will take on the Carolina Hurricanes in game one of the Eastern Conference Final after barely surviving game seven in each of their first two series. Montreal, despite being outshot 29-9 and going nearly 27 minutes without registering a shot on goal, defeated Tampa Bay courtesy of Alex Newhook's goal at 11:07 of the 3rd period. They were outplayed by the Buffalo Sabres in their next game seven, albeit not as dramatically, yet won again courtesy of another timely Newhook goal. Does Montreal deserve to be playing in the ECF? Of course they do! Luck and randomness are part of hockey, and so far Montreal has had the Hockey Gods on their side. Can Montreal endure another two game sevens the same way to reclaim the Stanley Cup for Canada for the first time since 1993 when they last won it all? Statistics suggests it is possible but unlikely.

#### Quantifying the Hockey Gods
Success in any pursuit, whether it be winning the Stanley Cup, or scoring a perfect 1600 on the SATs, or winning the lottery, requires a certain degree of skill and a certain degree of luck. The statistical framework called [True Score Theory](https://conjointly.com/kb/true-score-theory/) provides a model for quantifying just how much luck vs. how much skill may be involved in any of these endeavors. One would intuitively think that it takes more skill than luck to score a perfect 1600 on the SATs. Likewise, one would think that winning the lottery is inherently lucky because even a child possesses enough skill to come up with a set of Powerball numbers. Consider the following formula:

> variance(observed outcome) = variance(skill) + variance(luck)

We can easily estimate the variance of luck and calculate the variance of the observed outcome using the NHL standings after a full 82-game season. Knowing these two terms of the equation allows us to solve for the estimated variance of skill. Consider the probability of winning a hockey game after stripping out all skill. It is a coin toss. If all things are equal, I would expect my team to win 41 games and lose 41 games per season and earn a total of 82 points out of a maximum 164 possible. We can calculate the variance of luck by plugging what we know into its formula below, where `p` is probability of winning (0.50) and `n` is the number of games played in a season (82):

```
var_of_luck = p * (1 - p) / n
var_of_luck = 0.5 * (1 - 0.5) / 82
var_of_luck = 0.003049
```

Now let's look at the variance of total NHL winning percentages for all teams for the 2025-26 season:

```
win_percentages = [.738, .689, .683, .665, .646, .646, .634, .610,
                   .604, .598, .598, .579, .579, .567, .561, .561,
                   .561, .561, .555, .549, .530, .524, .524, .524,
                   .512, .500, .482, .476, .470, .470, .439, .354]

np.var(win_percentages) = 0.006249
```

We can estimate the variance of skill by plugging these values into our original equation:

```
var_of_skill = 0.006249 - 0.003049
var_of_skill = 0.0032
```

**Michael Mauboussin** introduces this approach to thinking about luck and skill in sports in his book [The Success Equation: Untangling Skill and Luck in Business, Sports, and Investing](https://www.amazon.com/Success-Equation-Untangling-Business-Investing/dp/1422184234). Mauboussin uses True Score Theory to create a theoretical continuum ranging from 100% luck (and 0% skill) to 0% luck (and 100% skill). You can place any endeavor along this continuum by dividing the contribution of luck by the observed outcome. Following along with our example, the variance of luck divided by the variance of the observed outcome suggests that luck contributed 49% of the resulting standings for the 2025-26 season.

```
0.003049 / 0.006249 = 0.487918
```

This places hockey in the middle of Mauboussin's continuum:
![Luck-skill continuum](/assets/mauboussin-luck-skill-continuum.jpg)

And our results are roughly in line with Mauboussin's 53% estimate for the five NHL seasons ending in 2012:
![Sports comps](/assets/mauboussin-table4-1.jpg)

Let's think about this for a second. We determined that hockey is far more random than basketball just by looking at the parity in the NHL and relative lackthereof in the NBA over their respective 82 game seasons. There are many reasons why this holds true. The first statistical rule has to do with the number of players involved and how they impact the game. Generally, the more players participate, the more randomness will play a role in the sport. Basketball and hockey both have five people playing at any time, assuming you do not count the goaltenders. However, hockey has on-the-fly line changes whereas basketball players can only be subbed in during stoppages. Each hockey game features eighteen skaters while the typical basetball rotation only has ten to twelve players. This brings us to a second statistical rule: larger sample sizes has less variance. The best hockey players typically only play 30-40% per game. The best basketball players play over 80% of each game. Also, the best basketball players also tend to dominate possession whereas much of a hockey game is spent with neither team having true possession of the puck. During his peak years, I imagine Kobe Bryant had the ball in his hands for just about every Lakers possession. The most elite hockey players in the world only truly possess the puck for 2-3 minutes per game.

![Hockey possession per game leaders](/assets/hockey-possession.png)

Ultimately this means that the most skilled basketball players drive gameplay much more often per game than the best hockey players do. While there are many other reasons why hockey is random, I think the point is clear by now: luck and randomness play a large role in determining the outcome of hockey games.


#### The Hockey Gods May Giveth, But They Also Taketh Away
Activities that involve significant amounts of luck tend to show strong reversion to the mean. Mauboussin introduces a useful concept for quantifying this: the **shrinking factor**. The formula is straightforward:

> Expected result = average + shrinking factor x (observed result - average)

A shrinking factor of 1 means the activity is all skill — there is no reversion, and the observed result is the best predictor of future performance. A shrinking factor of 0 means the activity is all luck — the best prediction for the next outcome is simply the base rate.

To illustrate: in baseball, the shrinking factor for batting average is approximately 0.20. If a player is hitting .350 early in the season, the expected year-end average would be .265 + 0.20 x (.350 - .265) = **.282** — much closer to the league average than the hot start would suggest. The observed result tells us surprisingly little about the player’s true ability.

In hockey, where luck accounts for roughly 53% of observed outcomes, we should expect even more aggressive reversion. A player who posts exceptional plus-minus numbers over a 30-game stretch is far more likely to regress toward the mean than to sustain that pace. This doesn’t mean the player lacks skill — it means the metric is capturing a large amount of noise alongside the signal.

This is precisely why, in domains with high luck, it is more valuable to focus on the **underlying process** rather than the observed outcomes. Results like wins, losses, goals, assists, and points may deviate considerably from what would be expected over the long term. Process-driven metrics — like expected goals — attempt to measure the quality of chances created and allowed, stripping away some of the randomness that contaminates traditional stats.

#### Don't Be Fooled By Randomness
If most hockey statistics revert to the mean, which ones are actually worth paying attention to? Mauboussin proposes two criteria for evaluating any performance metric:

1. **Persistence (reliability)** — Does the statistic correlate with itself year over year? If a player ranks highly in a metric one season, do they tend to rank highly the next? High persistence suggests the metric is capturing something real and repeatable — skill rather than luck.

2. **Predictability (validity)** — Does the statistic correlate with the outcome you actually care about? A metric can be highly persistent but ultimately irrelevant if it doesn’t help predict wins, goals, or other meaningful results.

The most useful statistics score highly on **both** dimensions. In hockey, the year-over-year correlations are revealing:

- **Shots on goal per minute**: r = 0.89 — very persistent. A player’s shot generation rate is largely a function of skill, playing style, and deployment.
- **Shooting percentage**: r = 0.63 — moderately persistent. There is a skill component, but a meaningful portion of the variance is attributable to luck.
- **Plus-minus**: r = 0.32 — weakly persistent. This is a stat heavily influenced by teammates, opponents, goaltending, and random bounces. Its low reliability makes it a poor indicator of individual skill.

A key insight emerges: **the more a statistic depends on the interaction of teammates and opponents, the lower its year-over-year correlation tends to be.** Plus-minus is a team-dependent outcome masquerading as an individual stat. Shooting percentage depends on shot quality, goaltender performance, and deflections. Shots per minute, by contrast, is more directly within a player’s control.

This framework is what motivated the approach taken on this site. Rather than relying on traditional box-score statistics, I used event data to calculate each player’s on-ice expected goals for and against. Expected goal metrics attempt to isolate the quality of the process — the chances created and allowed — from the randomness of whether the puck happened to go in. For defensemen in particular, xG provides a more accurate reflection of on-ice performance than goals, assists, or plus-minus.
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
