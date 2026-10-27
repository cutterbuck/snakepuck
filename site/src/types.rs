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

/// Game situation; the marts prefix each situational stat column with it (`pp_goals`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Situation {
    #[default]
    Tot,
    Es,
    Ev5,
    Pp,
    Pk,
}

impl Situation {
    pub const ALL: [Situation; 5] = [Self::Tot, Self::Es, Self::Ev5, Self::Pp, Self::Pk];
}

/// Season stats in one situation (`fct_player_season_stats`, `<situation>_*` columns).
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct SeasonStats {
    /// Average time on ice, seconds.
    pub atoi: f64,
    pub goals: i64,
    pub assists: i64,
    pub points: i64,
    pub shots: i64,
    pub shooting_pct: Option<f64>,
    pub faceoffs_won: i64,
    pub faceoffs_lost: i64,
    pub faceoff_pct: Option<f64>,
    pub blocks: i64,
    pub checks: i64,
    pub i_xg: f64,
    pub oi_xgf: f64,
    pub oi_xga: f64,
    pub xg_pct: Option<f64>,
}

/// Column to sort a player table by.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SortField {
    Name,
    Team,
    Position,
    Age,
    GamesPlayed,
    Atoi,
    Goals,
    Assists,
    #[default]
    Points,
    Shots,
    ShootingPct,
    FaceoffsWon,
    FaceoffsLost,
    FaceoffPct,
    Blocks,
    Checks,
    IXg,
    OiXgf,
    OiXga,
    XgPct,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Dir {
    Asc,
    #[default]
    Desc,
}

/// One player-team-season in one situation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PlayerSeasonLine {
    pub player_id: String,
    pub full_name: String,
    pub last_name: String,
    pub position: String,
    pub position_group: String,
    pub season: String,
    pub team_abbr: String,
    pub team_name: String,
    pub logo_url: String,
    pub age: i64,
    pub games_played: i64,
    #[serde(flatten)]
    pub stats: SeasonStats,
}

/// `/api/player-stats` parameters, and the Player Stats page's URL: every field is
/// optional, and defaults are left out when serialized.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct PlayerStatsQuery {
    /// Default: the AHL, or the first league.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub league: Option<String>,
    /// Default: the league's newest season.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub season: Option<String>,
    #[serde(default, skip_serializing_if = "is_default")]
    pub situation: Situation,
    #[serde(default, skip_serializing_if = "is_default")]
    pub sort: SortField,
    #[serde(default, skip_serializing_if = "is_default")]
    pub dir: Dir,
    /// From 1. Past the last page means the last page.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub page: Option<usize>,
}

/// How a player table is shown: `?situation=pp&sort=goals&dir=asc` (Team Detail's URL
/// and `/api/teams/...`). Defaults are left out when serialized.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct TableQuery {
    #[serde(default, skip_serializing_if = "is_default")]
    pub situation: Situation,
    #[serde(default, skip_serializing_if = "is_default")]
    pub sort: SortField,
    #[serde(default, skip_serializing_if = "is_default")]
    pub dir: Dir,
}

fn is_default<T: Default + PartialEq>(v: &T) -> bool {
    *v == T::default()
}

/// The Player Stats page: one page of a league-season's players, sorted.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PlayerStats {
    pub league: String,
    pub season: String,
    /// Newest first.
    pub seasons: Vec<Season>,
    pub situation: Situation,
    pub sort: SortField,
    pub dir: Dir,
    /// Rows across all pages.
    pub total: usize,
    pub page: usize,
    pub page_size: usize,
    pub rows: Vec<PlayerSeasonLine>,
}

/// Team Detail: one team-season's roster.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TeamDetail {
    pub team_abbr: String,
    pub team_name: String,
    pub logo_url: String,
    pub division: String,
    pub league: String,
    pub season: String,
    /// Seasons this team has stats for, newest first (the season dropdown).
    pub seasons: Vec<String>,
    pub situation: Situation,
    pub sort: SortField,
    pub dir: Dir,
    /// Sorted as asked.
    pub skaters: Vec<PlayerSeasonLine>,
    /// Always most games played first, below the skaters.
    pub goalies: Vec<PlayerSeasonLine>,
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn player_stats_query_leaves_defaults_out_of_the_url() {
        assert_eq!(
            serde_urlencoded::to_string(PlayerStatsQuery::default()).unwrap(),
            ""
        );
        let q = PlayerStatsQuery {
            league: Some("AHL".into()),
            sort: SortField::IXg,
            dir: Dir::Asc,
            page: Some(3),
            ..Default::default()
        };
        let url = serde_urlencoded::to_string(&q).unwrap();
        assert_eq!(url, "league=AHL&sort=i_xg&dir=asc&page=3");
        assert_eq!(
            serde_urlencoded::from_str::<PlayerStatsQuery>(&url).unwrap(),
            q
        );
    }
}
