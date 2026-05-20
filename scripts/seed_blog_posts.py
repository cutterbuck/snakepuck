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
        "title": "HALO Project Intro",
        "slug": "project-intro-dzone-puck-retrievals",
        "published_at": datetime(2026, 2, 19),
        "summary": (
            "Analyzing defensemen's D-zone loose puck retrievals using AHL "
            "player tracking data to evaluate how well they manage forecheck "
            "pressure and limit opponent scoring chances."
        ),
        "content": """\
## Defensemen D-zone Puck Retrievals
Elliotte Friedman recently noted on the 32 Thought Podcast that hockey operations departments throughout the NHL are still searching for ways to enhance analytics for defensemen. With this in mind, my initial attempt at extracting meaningful insights from the data will focus on evaluating defensive performance.
My perspective on hockey analytics is significantly shaped by Michael Mauboussin’s book, [The Success Equation: Untangling Skill and Luck in Business, Sports, and Investing](https://www.amazon.com/Success-Equation-Untangling-Business-Investing/dp/1422184234). In this work, Mauboussin introduces a theoretical continuum ranging from 100% luck to 100% skill. He notes that success in domains such as chess is almost entirely attributable to skill, while outcomes in games like roulette are determined predominantly by luck. According to Mauboussin, hockey occupies a balanced position on this continuum, with approximately 53% of success attributed to luck.
![Luck-skill continuum](/assets/mauboussin_skill_vs_luck.jpg)
There are several rational explanations for this, particularly when considering a limited sample size such as a seven-game playoff series. Numerous factors can significantly influence the outcome, including an exceptionally performing opposing goaltender, unfavorable goalie interference reviews, or an unpredictable deflection off a linesman’s skate leading to a scoring opportunity. Hockey is inherently a dynamic sport characterized by considerable randomness. Upon examining some of the raw data, it becomes evident that much of what occurs during a game is attributable to chance. Even elite players typically participate for only around 20 minutes per game and may possess the puck for just 1-2% of total playtime.

### D-zone LPRs Effect on On-ice Expected Goals
Activities that involve significant amounts of luck tend to show strong mean reversion. In hockey, it's more valuable to focus on the underlying process rather than just the observed outcomes, since results like wins, losses, goals, assists, and points may deviate considerably from what would be expected over the long term. Therefore, I used event data to calculate each player’s on-ice expected goals for and against. Expected goal metrics for defensemen provide a more accurate reflection of their performance on the ice compared to traditional stats like goals, assists, or plus-minus ratings.

I analyzed all defensemen's loose puck recoveries at 5-on-5 over 30 games to determine which players effectively retrieve dump-ins and limit opponent scoring chances from the forecheck. For each play, I calculated on-ice expected goals for and against from the moment of the loose puck recovery through the end of each shift or up until a faceoff occurs.

I examined low pressure loose puck recovery—when a defenseman has time and space to retrieve the puck. The outcomes and averages from 11,945 such recoveries are shown below.

![low-press-lpr](/assets/low-pressure-def-lpr.png)

I analyzed high-pressure loose puck recovery events to compare defensemen's performance under forechecking pressure. The average expected goals for percentage drops from 47.9% without pressure to 43.0% with significant forechecking, which reflects increased turnover risk when defensemen are pressured in their own zone.
![high-press-lpr](/assets/high-pressure-def-lpr.png)
This analysis also examines the change in a player’s expected goals percentage following a contested high-pressure loose puck recovery, specifically when the player successfully completes a safe play within the subsequent five seconds. Successful plays are defined as any effective pass, dump-out, puck protection, assist, penalty drawn, or controlled breakout event. The results indicate that executing a successful play under pressure elevates the average expected goals percentage to 49.8%, which is marginally higher than the rate observed for low-pressure defensive zone puck recoveries.

![high-press-lpr-success](/assets/high-pressure-def-lpr-next-success.png)
Lastly, I analyzed what happens when defensemen are unable to make a successful play within five seconds of recovering a contested loose puck. For this table, any failedpasslocation events, or unsuccessful pass, puck protection, or dump out attempts, are included. This is logical: when a defenseman has difficulty executing a safe move, it increases the odds that the opposing team will take control and create scoring opportunities.

![high-press-lpr-failure](/assets/high-pressure-def-lpr-next-failure.png)

After evaluation all high-pressure loose puck recoveries, I rated defensemen based on how well they manage forecheck pressure. The table ranks them by their success in making safe plays after recovering contested loose pucks.
![ hipress-def-lpr-success-rate](/assets/hipress-def-lpr-success-rate.png)

### Conclusions
Drawing clear conclusions from this analysis is challenging. As Howard Marks notes, "Not everything which counts can be counted and not everything which is counted counts." Mauboussin suggests statistics are useful only if they are predictable and reliable. Predictable statistics forecast desired outcomes—such as whether a defenseman's loose puck recovery rate leads to more wins—while reliability means reproducibility across samples. For instance, if Matthew Robertson consistently ranks highly in different 30-game samples, we can confirm his skill under forechecking pressure.

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
