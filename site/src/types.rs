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

/// Game stats in one situation (`fct_player_game_stats`, `<situation>_*` columns).
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct GameStats {
    /// Time on ice, seconds.
    pub toi: f64,
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

/// `?situation=pp` (Player Detail's URL and `/api/players/...`).
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct SituationQuery {
    #[serde(default, skip_serializing_if = "is_default")]
    pub situation: Situation,
}

/// The Game Report page's URL: `?situation=pp&period=2&shift=5`. Only the situation
/// goes to the API's report; the shift picks the rink's data.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct GameReportQuery {
    #[serde(default, skip_serializing_if = "is_default")]
    pub situation: Situation,
    /// The shift table's period: a number, or `all`. Default: the selected shift's
    /// period, otherwise the player's first.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub period: Option<String>,
    /// The shift on the rink.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub shift: Option<i64>,
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

/// A team as other responses reference it.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TeamInfo {
    pub team_abbr: String,
    pub team_name: String,
    pub logo_url: String,
}

/// Player Detail: season stats and the game log, in one situation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PlayerDetail {
    pub player_id: String,
    pub full_name: String,
    pub position: String,
    /// The team and season of their most recent game.
    pub latest_team: Option<LatestTeam>,
    pub situation: Situation,
    /// Oldest season first; within a season, the team they played most for first.
    pub seasons: Vec<PlayerSeasonLine>,
    /// Newest game first.
    pub games: Vec<GameLogLine>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LatestTeam {
    #[serde(flatten)]
    pub team: TeamInfo,
    pub season: String,
}

/// One of a player's games, as the game log shows it.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GameLogLine {
    pub game_id: String,
    pub game_date: String,
    pub team: TeamInfo,
    pub opponent: TeamInfo,
    pub is_home: bool,
    /// W, OTW, SOW, L, OTL or SOL.
    pub result: String,
    pub team_score: i64,
    pub opp_score: i64,
    #[serde(flatten)]
    pub stats: GameStats,
}

/// `fct_shifts`
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Shift {
    #[serde(default, skip_serializing)]
    pub player_id: String,
    pub shift: i64,
    pub period: i64,
    pub period_time_start: f64,
    pub period_time_end: f64,
    pub toi: f64,
    pub n_home_skaters: i64,
    pub n_away_skaters: i64,
    pub is_home_net_empty: bool,
    pub is_away_net_empty: bool,
    pub home_score: i64,
    pub away_score: i64,
    pub i_xg: f64,
    pub oi_xgf: f64,
    pub oi_xga: f64,
}

/// `fct_stints`, all-situations stats only (the marts' `tot_` columns). Goalies have
/// no shift.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Stint {
    #[serde(default, skip_serializing)]
    pub player_id: String,
    pub shift: Option<i64>,
    pub game_stint: i64,
    pub period: i64,
    pub period_time_start: f64,
    pub period_time_end: f64,
    pub n_home_skaters: i64,
    pub n_away_skaters: i64,
    pub is_home_net_empty: bool,
    pub is_away_net_empty: bool,
    pub home_score: i64,
    pub away_score: i64,
    pub toi: f64,
    pub i_xg: f64,
    pub oi_xgf: f64,
    pub oi_xga: f64,
}

/// `fct_game_events`. Events with no player (stoppages, period ends) have no team or location.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Event {
    pub sl_event_id: i64,
    #[serde(default, skip_serializing)]
    pub period: i64,
    pub period_time: f64,
    pub player_id: Option<String>,
    pub team_abbr: Option<String>,
    pub event_type: String,
    pub outcome: Option<String>,
    pub description: String,
    pub detail: String,
    pub flags: Option<String>,
    pub x: Option<f64>,
    pub y: Option<f64>,
}

/// `fct_tracking_snapshots`: one skater's position at one event. Skaters HALO couldn't
/// identify have no player_id.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Snapshot {
    #[serde(default, skip_serializing)]
    pub sl_event_id: i64,
    pub team_abbr: String,
    pub player_id: Option<String>,
    pub last_name: Option<String>,
    pub display_name: String,
    pub tracking_x: f64,
    pub tracking_y: f64,
}

/// A game as the Game Report heads it.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GameHeader {
    pub game_id: String,
    pub game_date: String,
    pub season: String,
    pub home: TeamInfo,
    pub away: TeamInfo,
    pub home_score: i64,
    pub away_score: i64,
}

/// Game Report: one player's stat line, shifts and stints in one game.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GameReport {
    pub game: GameHeader,
    pub player_id: String,
    pub full_name: String,
    pub position: String,
    pub team_abbr: String,
    pub is_home: bool,
    /// W, OTW, SOW, L, OTL or SOL.
    pub result: String,
    pub team_score: i64,
    pub opp_score: i64,
    /// All situations.
    pub penalties: i64,
    pub penalties_drawn: i64,
    pub situation: Situation,
    pub stats: GameStats,
    pub has_tracking: bool,
    /// Periods the player had a shift in.
    pub periods: Vec<i64>,
    pub shifts: Vec<Shift>,
    /// Every stint of the player's shifts, in order (`shift` says whose).
    pub stints: Vec<Stint>,
}

/// One event and every tracked skater's position at that moment.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Frame {
    #[serde(flatten)]
    pub event: Event,
    pub skaters: Vec<Snapshot>,
}

/// The rink for one shift: the stints it spans, and a frame per event in its window.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ShiftDetail {
    pub shift: Shift,
    pub stints: Vec<Stint>,
    /// Every event in the shift's time window, in time order.
    pub frames: Vec<Frame>,
}

/// `fct_defense_lpr`: one defenseman in one view of the Player Analysis LPR table.
/// The xG views fill the xG fields; the rate view fills the success fields.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct DefenseLpr {
    pub player_id: String,
    #[serde(default, skip_serializing)]
    pub view: String,
    pub games_played: i64,
    pub lpr_count: i64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub avg_oi_xgf: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub avg_oi_xga: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub total_oi_xgf: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub total_oi_xga: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub xg_pct: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub successes: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub failures: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub success_rate: Option<f64>,
}

/// A Player Analysis LPR table (see `fct_defense_lpr`).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LprView {
    Low,
    #[default]
    High,
    HighNextSuccess,
    HighNextFailure,
    HighNextRate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LprSortField {
    AvgOiXgf,
    AvgOiXga,
    TotalOiXgf,
    TotalOiXga,
    XgPct,
    Successes,
    Failures,
    SuccessRate,
}

/// `/api/player-analysis/defense-lpr` parameters, and the Player Analysis page's URL.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct LprQuery {
    #[serde(default, skip_serializing_if = "is_default")]
    pub view: LprView,
    /// Default: xG% for the xG views, success rate for the rate view (as on Dash).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub sort: Option<LprSortField>,
    #[serde(default, skip_serializing_if = "is_default")]
    pub dir: Dir,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LprRow {
    pub full_name: String,
    #[serde(flatten)]
    pub stats: DefenseLpr,
}

/// The Total row: counts and xG summed, averages and percentages averaged over the
/// listed defensemen. A view's fields only.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct LprTotals {
    pub lpr_count: i64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub avg_oi_xgf: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub avg_oi_xga: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub total_oi_xgf: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub total_oi_xga: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub xg_pct: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub successes: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub failures: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub success_rate: Option<f64>,
}

/// One LPR view: defensemen meeting the minimums, sorted, with totals.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LprTable {
    pub view: LprView,
    pub sort: LprSortField,
    pub dir: Dir,
    pub min_games_played: i64,
    pub min_lprs: i64,
    pub totals: LprTotals,
    pub rows: Vec<LprRow>,
}

/// The Sample Data page's URL: `?table=games`.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct SampleQuery {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub table: Option<String>,
}

/// A sample's rows as stored: each a JSON object of column to value.
pub type SampleRows = Vec<serde_json::Map<String, serde_json::Value>>;

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

    /// The browser reads back what the API writes: fields the API leaves out come back
    /// as defaults.
    #[test]
    fn shift_detail_survives_the_json_round_trip() {
        let stint = Stint {
            shift: Some(3),
            game_stint: 7,
            toi: 41.5,
            i_xg: 0.25,
            ..Default::default()
        };
        let detail = ShiftDetail {
            shift: Shift {
                shift: 3,
                ..Default::default()
            },
            stints: vec![stint],
            frames: vec![Frame {
                event: Event {
                    sl_event_id: 9,
                    event_type: "shot".into(),
                    x: Some(80.0),
                    ..Default::default()
                },
                skaters: vec![Snapshot {
                    display_name: "Ann Alpha".into(),
                    ..Default::default()
                }],
            }],
        };
        let json = serde_json::to_value(&detail).unwrap();
        assert_eq!(json["stints"][0]["toi"], 41.5);
        assert_eq!(serde_json::from_value::<ShiftDetail>(json).unwrap(), detail);
    }
}
