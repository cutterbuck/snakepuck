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

/// A league-season with data.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Season {
    pub league: String,
    pub season: String,
}

/// `fct_team_season_stats`: one team's record in a season.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct TeamSeason {
    pub team_abbr: String,
    pub season: String,
    pub games_played: i64,
    pub wins: i64,
    pub losses: i64,
    pub ot_losses: i64,
    pub points: i64,
    pub points_percentage: f64,
    pub regulation_wins: i64,
    pub regulation_or_ot_wins: i64,
    pub goals_forward: i64,
    pub goals_against: i64,
    pub goal_diff: i64,
    pub so_record: String,
}

/// The Standings page: one league-season, plus every league-season for the dropdowns.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Standings {
    pub league: String,
    pub season: String,
    /// Newest first.
    pub seasons: Vec<Season>,
    /// Ordered by points, then RW, ROW and W (the Dash page's tiebreakers).
    pub rows: Vec<StandingsRow>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StandingsRow {
    pub team_name: String,
    pub logo_url: String,
    pub division: String,
    #[serde(flatten)]
    pub stats: TeamSeason,
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
