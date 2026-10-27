//! Standings, Player Stats, Team Detail and Player Detail.

use std::cmp::Ordering;

use axum::Json;
use axum::extract::{Path, Query, State};
use serde::Deserialize;

use super::{ApiError, AppState, TeamRef, not_found};
use crate::server::data::{Player, PlayerSeason, Season, SeasonStats, Situation, Store};
use crate::types::{
    Dir, GameLogLine, LatestTeam, PlayerDetail, PlayerSeasonLine, PlayerStats, PlayerStatsQuery,
    SituationQuery, SortField, Standings, StandingsRow, TableQuery, TeamDetail,
};

/// Rows per page on Player Stats.
pub const PAGE_SIZE: usize = 25;

pub async fn seasons(State(store): State<AppState>) -> Json<Vec<Season>> {
    Json(store.seasons.clone())
}

/// The league, defaulting to the AHL (or the first league), and the season, defaulting
/// to the league's newest.
fn league_season(
    store: &Store,
    league: Option<String>,
    season: Option<String>,
    what: &str,
) -> Result<(String, String), ApiError> {
    let seasons = &store.seasons;
    let league = league
        .or_else(|| {
            let ahl = seasons.iter().find(|s| s.league == "AHL");
            ahl.or(seasons.first()).map(|s| s.league.clone())
        })
        .ok_or_else(|| not_found("seasons"))?;
    let season = season
        .or_else(|| {
            let newest = seasons.iter().find(|s| s.league == league);
            newest.map(|s| s.season.clone())
        })
        .ok_or_else(|| not_found(format!("{what} for {league}")))?;
    Ok((league, season))
}

/// Both optional (see `league_season`).
#[derive(Debug, Default, Deserialize)]
pub struct StandingsQuery {
    pub league: Option<String>,
    pub season: Option<String>,
}

/// Standings for one league-season, ordered by points, then RW, ROW and W
/// (the tiebreakers the Dash page uses).
pub fn standings(store: &Store, q: StandingsQuery) -> Result<Standings, ApiError> {
    let (league, season) = league_season(store, q.league, q.season, "standings")?;
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
        seasons: store.seasons.clone(),
        rows,
    })
}

pub async fn standings_handler(
    State(store): State<AppState>,
    Query(q): Query<StandingsQuery>,
) -> Result<Json<Standings>, ApiError> {
    Ok(Json(standings(&store, q)?))
}

/// One player-team-season in one situation, borrowed from the store: what the tables
/// sort, before the rows they return become `PlayerSeasonLine`s.
struct PlayerSeasonOut<'a> {
    player_id: &'a str,
    full_name: &'a str,
    last_name: &'a str,
    position: &'a str,
    position_group: &'a str,
    season: &'a str,
    team: TeamRef<'a>,
    age: i64,
    games_played: i64,
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

    fn line(&self) -> PlayerSeasonLine {
        PlayerSeasonLine {
            player_id: self.player_id.into(),
            full_name: self.full_name.into(),
            last_name: self.last_name.into(),
            position: self.position.into(),
            position_group: self.position_group.into(),
            season: self.season.into(),
            team_abbr: self.team.team_abbr.into(),
            team_name: self.team.team_name.into(),
            logo_url: self.team.logo_url.into(),
            age: self.age,
            games_played: self.games_played,
            stats: self.stats.clone(),
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

/// One page of every player-team row in a league-season.
pub fn player_stats(store: &Store, q: PlayerStatsQuery) -> Result<PlayerStats, ApiError> {
    let (league, season) = league_season(store, q.league, q.season, "player stats")?;
    let indexes = store
        .player_seasons_by_league_season
        .get(&(league.clone(), season.clone()))
        .ok_or_else(|| not_found(format!("player stats for {league} {season}")))?;

    let mut rows: Vec<_> = indexes
        .iter()
        .map(|&i| PlayerSeasonOut::new(store, &store.player_seasons[i], q.situation))
        .collect();
    sort_players(&mut rows, q.sort, q.dir);

    let total = rows.len();
    let last_page = total.div_ceil(PAGE_SIZE).max(1);
    let page = q.page.unwrap_or(1).clamp(1, last_page);
    let rows = rows
        .iter()
        .skip((page - 1) * PAGE_SIZE)
        .take(PAGE_SIZE)
        .map(PlayerSeasonOut::line)
        .collect();
    Ok(PlayerStats {
        league,
        season,
        seasons: store.seasons.clone(),
        situation: q.situation,
        sort: q.sort,
        dir: q.dir,
        total,
        page,
        page_size: PAGE_SIZE,
        rows,
    })
}

pub async fn player_stats_handler(
    State(store): State<AppState>,
    Query(q): Query<PlayerStatsQuery>,
) -> Result<Json<PlayerStats>, ApiError> {
    Ok(Json(player_stats(&store, q)?))
}

/// Team Detail: one team-season's roster, skaters then goalies.
pub fn team(
    store: &Store,
    team_abbr: &str,
    season: &str,
    t: TableQuery,
) -> Result<TeamDetail, ApiError> {
    let key = (team_abbr.to_string(), season.to_string());
    let (Some(team), Some(indexes)) = (
        store.teams.get(team_abbr),
        store.player_seasons_by_team_season.get(&key),
    ) else {
        return Err(not_found(format!("team {team_abbr} in {season}")));
    };

    let (mut goalies, mut skaters): (Vec<_>, Vec<_>) = indexes
        .iter()
        .map(|&i| PlayerSeasonOut::new(store, &store.player_seasons[i], t.situation))
        .partition(|p| p.position_group == "G");
    sort_players(&mut skaters, t.sort, t.dir);
    sort_players(&mut goalies, SortField::GamesPlayed, Dir::Desc);

    let seasons = store
        .seasons
        .iter()
        .filter(|s| {
            let key = (team_abbr.to_string(), s.season.clone());
            store.player_seasons_by_team_season.contains_key(&key)
        })
        .map(|s| s.season.clone())
        .collect();

    Ok(TeamDetail {
        team_abbr: team.team_abbr.clone(),
        team_name: team.team_name.clone(),
        logo_url: team.logo_url.clone(),
        division: team.division.clone(),
        league: team.league.clone(),
        season: season.to_string(),
        seasons,
        situation: t.situation,
        sort: t.sort,
        dir: t.dir,
        skaters: skaters.iter().map(PlayerSeasonOut::line).collect(),
        goalies: goalies.iter().map(PlayerSeasonOut::line).collect(),
    })
}

pub async fn team_handler(
    State(store): State<AppState>,
    Path((team_abbr, season)): Path<(String, String)>,
    Query(t): Query<TableQuery>,
) -> Result<Json<TeamDetail>, ApiError> {
    Ok(Json(team(&store, &team_abbr, &season, t)?))
}

/// Player Detail: season stats and the game log.
pub fn player(store: &Store, player_id: &str, q: SituationQuery) -> Result<PlayerDetail, ApiError> {
    let player = store
        .players
        .get(player_id)
        .ok_or_else(|| not_found(format!("player {player_id}")))?;

    let mut seasons: Vec<_> = store
        .player_seasons_by_player
        .get(player_id)
        .into_iter()
        .flatten()
        .map(|&i| PlayerSeasonOut::new(store, &store.player_seasons[i], q.situation))
        .collect();
    seasons.sort_by(|a, b| {
        a.season
            .cmp(b.season)
            .then(b.games_played.cmp(&a.games_played))
    });

    let games = store
        .player_games_by_player
        .get(player_id)
        .into_iter()
        .flatten()
        .map(|&i| {
            let pg = &store.player_games[i];
            let r = &pg.row;
            GameLogLine {
                game_id: r.game_id.clone(),
                game_date: store
                    .games
                    .get(&r.game_id)
                    .map_or(String::new(), |g| g.game_date.clone()),
                team: TeamRef::new(store, &r.team_abbr).info(),
                opponent: TeamRef::new(store, &r.opp_team_abbr).info(),
                is_home: r.is_home,
                result: r.result.clone(),
                team_score: r.team_score,
                opp_score: r.opp_score,
                stats: pg.stats(q.situation).clone(),
            }
        })
        .collect();

    let latest_team = store
        .player_games_by_player
        .get(player_id)
        .and_then(|rows| rows.first())
        .map(|&i| {
            let r = &store.player_games[i].row;
            LatestTeam {
                team: TeamRef::new(store, &r.team_abbr).info(),
                season: r.season.clone(),
            }
        });

    Ok(PlayerDetail {
        player_id: player.player_id.clone(),
        full_name: player.full_name.clone(),
        position: player.primary_position.clone(),
        latest_team,
        situation: q.situation,
        seasons: seasons.iter().map(PlayerSeasonOut::line).collect(),
        games,
    })
}

pub async fn player_handler(
    State(store): State<AppState>,
    Path(player_id): Path<String>,
    Query(q): Query<SituationQuery>,
) -> Result<Json<PlayerDetail>, ApiError> {
    Ok(Json(player(&store, &player_id, q)?))
}
