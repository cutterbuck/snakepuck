import dash_bootstrap_components as dbc
from dash import dcc, html


def create_about_layout():
    content = """\
## Exploring AHL Player Tracking Data
Welcome to Jake MacNaughton's HALO Project. This marks the beginning of what, time permitting, will become a series of blog posts. The purpose of this project is to gain familiarity with Teamworks and Sportlogiq AHL player data, aiming to extract meaningful signals from the vast array of player tracking and event data. By delving into millions of rows of this information, the goal is to uncover insights into player evaluation and team success that go beyond the traditional box-score statistics commonly found online.

### Processing and Visualizing Raw Player Tracking Data
This is my first experience handling player tracking data. Previously, I experimented with mapping data relationships for an application that tracked team and player performance at the season level. However, I have never worked with data at the game-by-game level, let alone the shift-by-shift or stint-by-stint granularity that this dataset provides. The data contains a 30 game sample for 1172 AHL players. There are parquet files for players, games, stints, events, and tracking data. This equates to 480 rows of games, over 1.8 millions rows of events that happen in these games, over 2.2 million stints, and over 13.5 million rows of tracking data.

While initially reviewing of the project's parquet files, I was overwhelmed by the depth and quantity of information they contained. How do these different datasets relate to one another? The only way for me to make any sense of the raw data was to first visualize it with a Flask app to see how it could be organized into a schema in the cleanest and simplest manner. You can view this data in the [Sample Raw Data](/sample-data) part of the Navbar. As a visual learner, looking at the raw data allowed me to figure out how to aggregate it into traditional player and team box score statistics. I also created simple expected goal analytics and aggregated a player's stats on a situational basis like Event Strength, 5-on-5, and so on. These efforts have made up the bulk of my work on this project to date. Naturally, unexpected things arise as you move forward with such a project. Certain edge cases became apparent, like dealing with players that played for multiple AHL teams over their 30 game sample size.

### Navigating this Site
The user experience is structured as follows: from the NAV bar, you can navigate to the [Team Standings](/team-standings) section. Here, you can select any team to view its roster and see player statistics for the 30-game sample provided. On the team page, you can click on any player to see his performance broken down game-by-game. You can then select any game to view the player's performance shift-by-shift. Finally, you can click on any shift to see all tracking and event data play out sequentially on a hockey rink visualization at the bottom of the page.

### Challenges and Discoveries
As a visual learner, proceeding with the project in this manner was essential. This approach proved valuable: by watching the player tracking and event data unfold on the hockey rink, I discovered that I had been using incorrect event coordinates. Initially, the tracking data seemed confusing because I relied on x_adj/y_adj, which rendered events as if a team's offensive zone was always to the right. For half a game, it appeared that the puck and all action happened on one side of the ice, while players skated aimlessly on the other. Any analysis of player performance would have been ineffective using these incorrect coordinates.

### Feedback and Future Improvements
I hope the visual renderings help users make sense of the tracking data. While the page structure made sense to me, it might not suit everyone. If you have suggestions for improving the user experience, please share your feedback, and I will make adjustments as needed.
"""

    return dbc.Container(
        [
            dcc.Markdown(content, className="blog-post-body"),
        ],
        fluid=True,
        style={"maxWidth": "900px", "margin": "0 auto"},
    )
