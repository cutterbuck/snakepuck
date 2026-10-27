//! Standings, Player Stats, Team Detail and Player Detail.

use std::cmp::Ordering;

use axum::Json;
use axum::extract::{Path, Query, State};
use axum::response::{IntoResponse, Response};
use serde::{Deserialize, Serialize};

use super::{ApiError, AppState, TeamRef, not_found};
use crate::server::data::{GameStats, Player, PlayerSeason, Season, SeasonStats, Situation, Store};
use crate::types::{Standings, StandingsRow};

/// Rows per page on Player Stats.
pub const PAGE_SIZE: usize = 25;

pub async fn seasons(State(store): State<AppState>) -> Json<Vec<Season>> {
    Json(store.seasons.clone())
}

/// Both optional: the league defaults to the AHL (or the first league), the season
/// to the league's newest.
#[derive(Debug, Default, Deserialize)]
pub struct StandingsQuery {
    pub league: Option<String>,
    pub season: Option<String>,
}

/// Standings for one league-season, ordered by points, then RW, ROW and W
/// (the tiebreakers the Dash page uses).
pub fn standings(store: &Store, q: StandingsQuery) -> Result<Standings, ApiError> {
    let seasons = &store.seasons;
    let league = q
        .league
        .or_else(|| {
            let ahl = seasons.iter().find(|s| s.league == "AHL");
            ahl.or(seasons.first()).map(|s| s.league.clone())
        })
        .ok_or_else(|| not_found("seasons"))?;
    let season = q
        .season
        .or_else(|| {
            let newest = seasons.iter().find(|s| s.league == league);
            newest.map(|s| s.season.clone())
        })
        .ok_or_else(|| not_found(format!("standings for {league}")))?;
    let rows = store
        .team_seasons
        .get(&(league.clone(), season.clone()))
        .ok_or_else(|| not_found(format!("standings for {league} {season}")))?;

    let mut rows: Vec<_> = rows
        .iter()
        .map(|ts| {
            let team = &store.teams[&ts.team_abbr];
            StandingsRow {
                team_name: team.team_name.clone(),
                logo_url: team.logo_url.clone(),
                division: team.division.clone(),
                stats: ts.clone(),
            }
        })
        .collect();
    rows.sort_by_key(|r| {
        let s = &r.stats;
        std::cmp::Reverse((s.points, s.regulation_wins, s.regulation_or_ot_wins, s.wins))
    });
    Ok(Standings {
        league,
        season,
        seasons: seasons.clone(),
        rows,
    })
}

pub async fn standings_handler(
    State(store): State<AppState>,
    Query(q): Query<StandingsQuery>,
) -> Result<Json<Standings>, ApiError> {
    Ok(Json(standings(&store, q)?))
}

/// Column to sort a player table by.
#[derive(Debug, Clone, Copy, Default, Deserialize)]
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

#[derive(Debug, Clone, Copy, Default, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Dir {
    Asc,
    #[default]
    Desc,
}

#[derive(Deserialize)]
pub struct TableQuery {
    #[serde(default)]
    situation: Situation,
    #[serde(default)]
    sort: SortField,
    #[serde(default)]
    dir: Dir,
}

/// One player-team-season in one situation.
#[derive(Serialize)]
pub struct PlayerSeasonOut<'a> {
    player_id: &'a str,
    full_name: &'a str,
    last_name: &'a str,
    position: &'a str,
    position_group: &'a str,
    season: &'a str,
    #[serde(flatten)]
    team: TeamRef<'a>,
    age: i64,
    games_played: i64,
    #[serde(flatten)]
    stats: &'a SeasonStats,
}

static UNKNOWN_PLAYER: std::sync::LazyLock<Player> = std::sync::LazyLock::new(Player::default);

impl<'a> PlayerSeasonOut<'a> {
    fn new(store: &'a Store, ps: &'a PlayerSeason, situation: Situation) -> Self {
        let player = store
            .players
            .get(&ps.row.player_id)
            .unwrap_or(&UNKNOWN_PLAYER);
        Self {
            player_id: &ps.row.player_id,
            full_name: &player.full_name,
            last_name: &player.last_name,
            position: &player.primary_position,
            position_group: &player.position_group,
            season: &ps.row.season,
            team: TeamRef::new(store, &ps.row.team_abbr),
            age: ps.row.age,
            games_played: ps.row.games_played,
            stats: ps.stats(situation),
        }
    }

    fn sort_key(&self, field: SortField) -> Option<SortKey<'a>> {
        use SortField::*;
        let s = self.stats;
        let num = |v: f64| Some(SortKey::Num(v));
        match field {
            Name => Some(SortKey::Text(self.last_name)),
            Team => Some(SortKey::Text(self.team.team_abbr)),
            Position => Some(SortKey::Text(self.position)),
            Age => num(self.age as f64),
            GamesPlayed => num(self.games_played as f64),
            Atoi => num(s.atoi),
            Goals => num(s.goals as f64),
            Assists => num(s.assists as f64),
            Points => num(s.points as f64),
            Shots => num(s.shots as f64),
            ShootingPct => s.shooting_pct.map(SortKey::Num),
            FaceoffsWon => num(s.faceoffs_won as f64),
            FaceoffsLost => num(s.faceoffs_lost as f64),
            FaceoffPct => s.faceoff_pct.map(SortKey::Num),
            Blocks => num(s.blocks as f64),
            Checks => num(s.checks as f64),
            IXg => num(s.i_xg),
            OiXgf => num(s.oi_xgf),
            OiXga => num(s.oi_xga),
            XgPct => s.xg_pct.map(SortKey::Num),
        }
    }
}

#[derive(PartialEq)]
enum SortKey<'a> {
    Num(f64),
    Text(&'a str),
}

impl SortKey<'_> {
    fn cmp(&self, other: &Self) -> Ordering {
        match (self, other) {
            (Self::Num(a), Self::Num(b)) => a.total_cmp(b),
            (Self::Text(a), Self::Text(b)) => a.cmp(b),
            _ => Ordering::Equal,
        }
    }
}

/// Sort by `field` in `dir`, with missing values (e.g. S% with no shots) last either way,
/// then by name so the order is stable.
fn sort_players(rows: &mut [PlayerSeasonOut], field: SortField, dir: Dir) {
    rows.sort_by(|a, b| {
        let by_field = match (a.sort_key(field), b.sort_key(field)) {
            (Some(x), Some(y)) => match dir {
                Dir::Asc => x.cmp(&y),
                Dir::Desc => y.cmp(&x),
            },
            (Some(_), None) => Ordering::Less,
            (None, Some(_)) => Ordering::Greater,
            (None, None) => Ordering::Equal,
        };
        by_field.then_with(|| a.full_name.cmp(b.full_name))
    });
}

#[derive(Deserialize)]
pub struct PlayerStatsQuery {
    league: String,
    season: String,
    #[serde(flatten)]
    table: TableQuery,
    #[serde(default = "first_page")]
    page: usize,
}

fn first_page() -> usize {
    1
}

#[derive(Serialize)]
pub struct PlayerStatsPage<'a> {
    total: usize,
    page: usize,
    page_size: usize,
    rows: Vec<PlayerSeasonOut<'a>>,
}

/// One page of every player-team row in a league-season.
pub async fn player_stats(
    State(store): State<AppState>,
    Query(q): Query<PlayerStatsQuery>,
) -> Result<Response, ApiError> {
    let indexes = store
        .player_seasons_by_league_season
        .get(&(q.league.clone(), q.season.clone()))
        .ok_or_else(|| not_found(format!("player stats for {} {}", q.league, q.season)))?;

    let t = &q.table;
    let mut rows: Vec<_> = indexes
        .iter()
        .map(|&i| PlayerSeasonOut::new(&store, &store.player_seasons[i], t.situation))
        .collect();
    sort_players(&mut rows, t.sort, t.dir);

    let total = rows.len();
    let page = q.page.max(1);
    let rows = rows
        .into_iter()
        .skip((page - 1) * PAGE_SIZE)
        .take(PAGE_SIZE)
        .collect();
    let body = PlayerStatsPage {
        total,
        page,
        page_size: PAGE_SIZE,
        rows,
    };
    Ok(Json(body).into_response())
}

#[derive(Serialize)]
pub struct TeamPage<'a> {
    #[serde(flatten)]
    team: TeamRef<'a>,
    division: &'a str,
    league: &'a str,
    season: &'a str,
    /// Seasons this team has stats for, newest first (the season dropdown).
    seasons: Vec<&'a str>,
    roster: Vec<PlayerSeasonOut<'a>>,
}

/// Team Detail: one team-season's roster.
pub async fn team(
    State(store): State<AppState>,
    Path((team_abbr, season)): Path<(String, String)>,
    Query(t): Query<TableQuery>,
) -> Result<Response, ApiError> {
    let key = (team_abbr.clone(), season.clone());
    let (Some(team), Some(indexes)) = (
        store.teams.get(&team_abbr),
        store.player_seasons_by_team_season.get(&key),
    ) else {
        return Err(not_found(format!("team {team_abbr} in {season}")));
    };

    let mut roster: Vec<_> = indexes
        .iter()
        .map(|&i| PlayerSeasonOut::new(&store, &store.player_seasons[i], t.situation))
        .collect();
    sort_players(&mut roster, t.sort, t.dir);

    let seasons = store
        .seasons
        .iter()
        .filter(|s| {
            let key = (team_abbr.clone(), s.season.clone());
            store.player_seasons_by_team_season.contains_key(&key)
        })
        .map(|s| s.season.as_str())
        .collect();

    let body = TeamPage {
        team: TeamRef::new(&store, &team.team_abbr),
        division: &team.division,
        league: &team.league,
        season: &season,
        seasons,
        roster,
    };
    Ok(Json(body).into_response())
}

#[derive(Deserialize)]
pub struct SituationQuery {
    #[serde(default)]
    pub situation: Situation,
}

/// A player's game, as the Player Detail game log shows it.
#[derive(Serialize)]
pub struct GameLogRow<'a> {
    game_id: &'a str,
    game_date: &'a str,
    team: TeamRef<'a>,
    opponent: TeamRef<'a>,
    is_home: bool,
    result: &'a str,
    team_score: i64,
    opp_score: i64,
    #[serde(flatten)]
    stats: &'a GameStats,
}

/// The team and season of a player's most recent game.
#[derive(Serialize)]
pub struct LatestTeam<'a> {
    #[serde(flatten)]
    team: TeamRef<'a>,
    season: &'a str,
}

#[derive(Serialize)]
pub struct PlayerPage<'a> {
    player_id: &'a str,
    full_name: &'a str,
    position: &'a str,
    latest_team: Option<LatestTeam<'a>>,
    /// Oldest season first; within a season, the team they played most for first.
    seasons: Vec<PlayerSeasonOut<'a>>,
    /// Newest game first.
    games: Vec<GameLogRow<'a>>,
}

/// Player Detail: season stats and the game log.
pub async fn player(
    State(store): State<AppState>,
    Path(player_id): Path<String>,
    Query(q): Query<SituationQuery>,
) -> Result<Response, ApiError> {
    let player = store
        .players
        .get(&player_id)
        .ok_or_else(|| not_found(format!("player {player_id}")))?;

    let mut seasons: Vec<_> = store
        .player_seasons_by_player
        .get(&player_id)
        .into_iter()
        .flatten()
        .map(|&i| PlayerSeasonOut::new(&store, &store.player_seasons[i], q.situation))
        .collect();
    seasons.sort_by(|a, b| {
        a.season
            .cmp(b.season)
            .then(b.games_played.cmp(&a.games_played))
    });

    let games: Vec<_> = store
        .player_games_by_player
        .get(&player_id)
        .into_iter()
        .flatten()
        .map(|&i| {
            let pg = &store.player_games[i];
            let r = &pg.row;
            GameLogRow {
                game_id: &r.game_id,
                game_date: store.games.get(&r.game_id).map_or("", |g| &g.game_date),
                team: TeamRef::new(&store, &r.team_abbr),
                opponent: TeamRef::new(&store, &r.opp_team_abbr),
                is_home: r.is_home,
                result: &r.result,
                team_score: r.team_score,
                opp_score: r.opp_score,
                stats: pg.stats(q.situation),
            }
        })
        .collect();

    let latest_team = store
        .player_games_by_player
        .get(&player_id)
        .and_then(|rows| rows.first())
        .map(|&i| {
            let r = &store.player_games[i].row;
            LatestTeam {
                team: TeamRef::new(&store, &r.team_abbr),
                season: &r.season,
            }
        });

    let body = PlayerPage {
        player_id: &player.player_id,
        full_name: &player.full_name,
        position: &player.primary_position,
        latest_team,
        seasons,
        games,
    };
    Ok(Json(body).into_response())
}
