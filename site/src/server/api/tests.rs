//! Endpoint tests against a small in-memory fixture (licensed data never enters tests).

use std::path::PathBuf;

use axum::body::{Body, Bytes};
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use super::router;
use crate::server::data::{
    DefenseLpr, Game, GameStats, Marts, Player, PlayerGameRow, PlayerSeasonRow, SeasonStats,
    Situational, Store, Team, TeamSeason,
};
use crate::server::games::{Event, GameFiles, Shift, Snapshot, Stint};

fn team(abbr: &str) -> Team {
    Team {
        team_abbr: abbr.into(),
        team_name: format!("{abbr} Team"),
        division: "Pacific".into(),
        league: "AHL".into(),
        logo_url: format!("https://logos/{abbr}.png"),
    }
}

fn player(id: &str, first: &str, last: &str, position: &str) -> Player {
    Player {
        player_id: id.into(),
        last_name: last.into(),
        full_name: format!("{first} {last}"),
        primary_position: position.into(),
        position_group: position.into(),
    }
}

fn game(id: &str, date: &str, season: &str, home: &str, away: &str) -> Game {
    Game {
        game_id: id.into(),
        game_date: date.into(),
        league: "AHL".into(),
        season: season.into(),
        home_team_abbr: home.into(),
        away_team_abbr: away.into(),
        home_score: 3,
        away_score: 2,
    }
}

fn team_season(abbr: &str, points: i64, regulation_wins: i64) -> TeamSeason {
    TeamSeason {
        team_abbr: abbr.into(),
        season: "2023-24".into(),
        points,
        regulation_wins,
        ..Default::default()
    }
}

/// Season row with `tot` stats; power-play goals are `pp_goals`, other situations zero.
fn player_season(
    id: &str,
    team: &str,
    games_played: i64,
    tot: SeasonStats,
    pp_goals: i64,
) -> Situational<PlayerSeasonRow, SeasonStats> {
    let row = PlayerSeasonRow {
        player_id: id.into(),
        team_abbr: team.into(),
        season: "2023-24".into(),
        games_played,
        age: 24,
    };
    let pp = SeasonStats {
        goals: pp_goals,
        ..Default::default()
    };
    Situational::new(
        row,
        [
            tot,
            Default::default(),
            Default::default(),
            pp,
            Default::default(),
        ],
    )
}

fn player_game(
    game_id: &str,
    is_home: bool,
    result: &str,
) -> Situational<PlayerGameRow, GameStats> {
    let row = PlayerGameRow {
        player_id: "p1".into(),
        game_id: game_id.into(),
        team_abbr: "ABB".into(),
        season: "2023-24".into(),
        is_home,
        opp_team_abbr: "BAK".into(),
        result: result.into(),
        ..Default::default()
    };
    let tot = GameStats {
        goals: 1,
        ..Default::default()
    };
    let pp = GameStats {
        goals: 7,
        ..Default::default()
    };
    Situational::new(
        row,
        [
            tot,
            Default::default(),
            Default::default(),
            pp,
            Default::default(),
        ],
    )
}

fn shift(player_id: &str, shift: i64, period: i64, start: f64, end: f64) -> Shift {
    Shift {
        player_id: player_id.into(),
        shift,
        period,
        period_time_start: start,
        period_time_end: end,
        ..Default::default()
    }
}

fn stint(player_id: &str, game_stint: i64, shift: Option<i64>) -> Stint {
    Stint {
        player_id: player_id.into(),
        game_stint,
        shift,
        ..Default::default()
    }
}

fn event(sl_event_id: i64, period: i64, period_time: f64) -> Event {
    Event {
        sl_event_id,
        period,
        period_time,
        event_type: "pass".into(),
        ..Default::default()
    }
}

fn snapshot(sl_event_id: i64, name: &str) -> Snapshot {
    Snapshot {
        sl_event_id,
        team_abbr: "ABB".into(),
        display_name: name.into(),
        ..Default::default()
    }
}

fn lpr_xg(
    player_id: &str,
    view: &str,
    games_played: i64,
    lpr_count: i64,
    xg_pct: f64,
) -> DefenseLpr {
    DefenseLpr {
        player_id: player_id.into(),
        view: view.into(),
        games_played,
        lpr_count,
        avg_oi_xgf: Some(0.02),
        avg_oi_xga: Some(0.01),
        total_oi_xgf: Some(0.4),
        total_oi_xga: Some(0.2),
        xg_pct: Some(xg_pct),
        ..Default::default()
    }
}

fn lpr_rate(player_id: &str, games_played: i64, successes: i64, failures: i64) -> DefenseLpr {
    DefenseLpr {
        player_id: player_id.into(),
        view: "high_next_rate".into(),
        games_played,
        lpr_count: successes + failures,
        successes: Some(successes),
        failures: Some(failures),
        success_rate: Some(successes as f64 / (successes + failures) as f64),
        ..Default::default()
    }
}

fn store() -> Store {
    let stats = |goals, points, shooting_pct| SeasonStats {
        goals,
        points,
        shooting_pct,
        ..Default::default()
    };
    let marts = Marts {
        teams: vec![team("ABB"), team("BAK"), team("CGY")],
        players: vec![
            player("p1", "Ann", "Alpha", "C"),
            player("p2", "Bob", "Beta", "D"),
            player("p3", "Cat", "Gamma", "G"),
            player("p4", "Dan", "Delta", "D"),
            player("p5", "Eve", "Epsilon", "D"),
        ],
        games: vec![
            game("g0", "2022-10-14", "2022-23", "CGY", "ABB"),
            game("g1", "2023-10-14", "2023-24", "ABB", "BAK"),
            game("g2", "2023-10-20", "2023-24", "BAK", "ABB"),
        ],
        team_seasons: vec![
            team_season("ABB", 90, 30),
            team_season("BAK", 95, 28),
            team_season("CGY", 90, 33),
        ],
        player_seasons: vec![
            player_season("p1", "ABB", 20, stats(5, 9, Some(0.2)), 2),
            player_season("p2", "ABB", 10, stats(1, 4, None), 3),
            player_season("p2", "BAK", 12, stats(2, 6, Some(0.1)), 0),
            player_season("p3", "ABB", 15, stats(0, 1, Some(0.0)), 0),
        ],
        player_games: vec![
            player_game("g1", true, "W"),
            player_game("g2", false, "OTL"),
        ],
        defense_lpr: vec![
            lpr_xg("p2", "high", 25, 20, 0.6),
            lpr_xg("p4", "high", 30, 16, 0.4),
            lpr_xg("p5", "high", 30, 10, 0.9), // too few LPRs
            lpr_xg("p1", "high", 10, 40, 0.9), // too few games
            lpr_rate("p2", 25, 14, 6),
            lpr_rate("p4", 30, 9, 7),
        ],
        samples: [(
            "players".to_string(),
            Bytes::from_static(br#"[{"player_id":"p1"}]"#),
        )]
        .into(),
    };
    let store = Store::new(marts, PathBuf::from("/nonexistent"));
    store.game_files.insert(
        "g1",
        GameFiles {
            shifts: vec![
                shift("p1", 1, 1, 0.0, 40.0),
                shift("p1", 2, 2, 100.0, 150.0),
                shift("p2", 1, 1, 0.0, 35.0),
            ],
            stints: vec![
                stint("p1", 1, Some(1)),
                stint("p1", 2, Some(1)),
                stint("p1", 5, Some(2)),
                stint("p3", 1, None),
            ],
            events: vec![
                event(10, 1, 5.0),
                event(11, 1, 30.0),
                event(12, 1, 60.0),
                event(13, 2, 120.0),
            ],
            tracking: vec![
                snapshot(10, "Alpha"),
                snapshot(10, "Beta"),
                snapshot(11, "Alpha"),
            ],
        },
    );
    store.game_files.insert(
        "g2",
        GameFiles {
            shifts: vec![shift("p1", 1, 1, 0.0, 40.0)],
            events: vec![event(1, 1, 10.0)],
            ..Default::default()
        },
    );
    store
}

async fn get(uri: &str) -> (StatusCode, Value) {
    let response = router(std::sync::Arc::new(store()))
        .oneshot(Request::get(uri).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&body).unwrap_or(Value::Null))
}

fn column<'a>(rows: &'a Value, field: &str) -> Vec<&'a Value> {
    rows.as_array().unwrap().iter().map(|r| &r[field]).collect()
}

#[tokio::test]
async fn seasons_newest_first() {
    let (status, body) = get("/api/seasons").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(column(&body, "season"), ["2023-24", "2022-23"]);
}

#[tokio::test]
async fn standings_sorted_by_points_then_regulation_wins() {
    let (status, body) = get("/api/standings?league=AHL&season=2023-24").await;
    assert_eq!(status, StatusCode::OK);
    let rows = &body["rows"];
    assert_eq!(column(rows, "team_abbr"), ["BAK", "CGY", "ABB"]);
    assert_eq!(rows[0]["team_name"], "BAK Team");
    assert_eq!(rows[0]["points"], 95);
}

#[tokio::test]
async fn standings_default_to_the_newest_season_and_list_every_season() {
    let (status, body) = get("/api/standings").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        (&body["league"], &body["season"]),
        (&"AHL".into(), &"2023-24".into())
    );
    assert_eq!(column(&body["seasons"], "season"), ["2023-24", "2022-23"]);
    assert_eq!(body["rows"].as_array().unwrap().len(), 3);
}

#[tokio::test]
async fn standings_unknown_season_is_404() {
    let (status, body) = get("/api/standings?league=AHL&season=1999-00").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert!(body["error"].as_str().unwrap().contains("1999-00"));
}

#[tokio::test]
async fn player_stats_default_sort_is_points_desc() {
    let (status, body) = get("/api/player-stats?league=AHL&season=2023-24").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["total"], 4);
    assert_eq!(body["page_size"], 25);
    assert_eq!(column(&body["rows"], "points"), [9, 6, 4, 1]);
    assert_eq!(body["rows"][0]["full_name"], "Ann Alpha");
    assert_eq!(body["rows"][0]["logo_url"], "https://logos/ABB.png");
}

#[tokio::test]
async fn player_stats_default_to_the_newest_season_and_echo_the_query() {
    let (status, body) = get("/api/player-stats?situation=pp&sort=goals&dir=asc").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        (&body["league"], &body["season"]),
        (&"AHL".into(), &"2023-24".into())
    );
    assert_eq!(column(&body["seasons"], "season"), ["2023-24", "2022-23"]);
    assert_eq!(
        (&body["situation"], &body["sort"], &body["dir"]),
        (&"pp".into(), &"goals".into(), &"asc".into())
    );
}

#[tokio::test]
async fn player_stats_serve_only_the_requested_situation() {
    let (_, body) =
        get("/api/player-stats?league=AHL&season=2023-24&situation=pp&sort=goals").await;
    assert_eq!(column(&body["rows"], "goals"), [3, 2, 0, 0]);
    assert!(body["rows"][0].get("pp_goals").is_none());
}

#[tokio::test]
async fn player_stats_missing_values_sort_last_both_ways() {
    for dir in ["asc", "desc"] {
        let uri =
            format!("/api/player-stats?league=AHL&season=2023-24&sort=shooting_pct&dir={dir}");
        let (_, body) = get(&uri).await;
        assert_eq!(body["rows"][3]["shooting_pct"], Value::Null, "dir={dir}");
    }
}

#[tokio::test]
async fn player_stats_pages_and_rejects_unknown_sort() {
    // Past the last page means the last page.
    let (_, body) = get("/api/player-stats?league=AHL&season=2023-24&page=2").await;
    assert_eq!(body["total"], 4);
    assert_eq!(body["page"], 1);
    assert_eq!(body["rows"].as_array().unwrap().len(), 4);

    let (status, _) = get("/api/player-stats?league=AHL&season=2023-24&sort=password").await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn team_roster_for_one_team_season() {
    let (status, body) = get("/api/teams/ABB/2023-24?sort=name&dir=asc").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["team_name"], "ABB Team");
    assert_eq!(body["seasons"], serde_json::json!(["2023-24"]));
    assert_eq!(column(&body["skaters"], "last_name"), ["Alpha", "Beta"]);
    assert_eq!(column(&body["goalies"], "last_name"), ["Gamma"]);

    // Goalies stay below the skaters, by games played, whatever the sort.
    let (_, body) = get("/api/teams/ABB/2023-24?sort=name&dir=desc").await;
    assert_eq!(column(&body["skaters"], "last_name"), ["Beta", "Alpha"]);
    assert_eq!(column(&body["goalies"], "last_name"), ["Gamma"]);

    let (status, _) = get("/api/teams/XXX/2023-24").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn player_detail_seasons_and_game_log() {
    let (status, body) = get("/api/players/p1?situation=pp").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["full_name"], "Ann Alpha");
    assert_eq!(body["latest_team"]["team_abbr"], "ABB");
    assert_eq!(body["latest_team"]["season"], "2023-24");
    assert_eq!(column(&body["games"], "game_id"), ["g2", "g1"]);
    assert_eq!(body["games"][0]["result"], "OTL");
    assert_eq!(body["games"][0]["opponent"]["team_abbr"], "BAK");
    assert_eq!(body["games"][0]["goals"], 7);

    let (_, body) = get("/api/players/p2").await;
    assert_eq!(
        column(&body["seasons"], "team_abbr"),
        ["BAK", "ABB"],
        "most games first"
    );
    assert_eq!(body["latest_team"], Value::Null);
}

#[tokio::test]
async fn game_report_is_one_player_game() {
    let (status, body) = get("/api/games/g1/players/p1?situation=pp").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["game"]["home"]["team_abbr"], "ABB");
    assert_eq!(body["result"], "W");
    assert_eq!(body["goals"], Value::Null, "stats are nested");
    assert_eq!(body["stats"]["goals"], 7);
    assert_eq!(body["has_tracking"], true);
    assert_eq!(body["periods"], serde_json::json!([1, 2]));
    assert_eq!(column(&body["shifts"], "shift"), [1, 2]);
    assert!(body["shifts"][0].get("player_id").is_none());
    // Their stints across both shifts; another player's (a goalie's, no shift) left out.
    assert_eq!(column(&body["stints"], "game_stint"), [1, 2, 5]);
    assert_eq!(column(&body["stints"], "shift"), [1, 1, 2]);
}

#[tokio::test]
async fn shift_frames_cover_only_the_shift_window() {
    let (status, body) = get("/api/games/g1/players/p1/shifts/1").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(column(&body["stints"], "game_stint"), [1, 2]);
    assert_eq!(column(&body["frames"], "sl_event_id"), [10, 11]);
    assert_eq!(
        column(&body["frames"][0]["skaters"], "display_name"),
        ["Alpha", "Beta"]
    );
    assert_eq!(body["frames"][1]["skaters"].as_array().unwrap().len(), 1);
}

#[tokio::test]
async fn game_without_tracking_has_frames_with_no_skaters() {
    let (_, body) = get("/api/games/g2/players/p1").await;
    assert_eq!(body["has_tracking"], false);
    let (status, body) = get("/api/games/g2/players/p1/shifts/1").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["frames"][0]["skaters"], Value::Array(vec![]));
}

#[tokio::test]
async fn unknown_games_players_and_shifts_are_404() {
    for uri in [
        "/api/games/g1/players/nobody",
        "/api/games/..%2F..%2Fetc/players/p1",
        "/api/games/g1/players/p1/shifts/99",
        "/api/players/nobody",
    ] {
        let (status, _) = get(uri).await;
        assert_eq!(status, StatusCode::NOT_FOUND, "{uri}");
    }
}

#[tokio::test]
async fn samples_are_served_as_stored() {
    let (status, body) = get("/api/sample/players").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body[0]["player_id"], "p1");
    let (status, _) = get("/api/sample/passwords").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn defense_lpr_lists_qualifying_defensemen_by_xg_pct() {
    let (status, body) = get("/api/player-analysis/defense-lpr").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["view"], "high");
    assert_eq!(
        column(&body["rows"], "full_name"),
        ["Bob Beta", "Dan Delta"]
    );
    assert_eq!(body["totals"]["lpr_count"], 36);
    assert!(
        (body["totals"]["xg_pct"].as_f64().unwrap() - 0.5).abs() < 1e-9,
        "mean of rows"
    );
    assert!(
        body["rows"][0].get("success_rate").is_none(),
        "rate fields left out"
    );

    let (_, body) = get("/api/player-analysis/defense-lpr?sort=xg_pct&dir=asc").await;
    assert_eq!(
        column(&body["rows"], "full_name"),
        ["Dan Delta", "Bob Beta"]
    );
}

#[tokio::test]
async fn defense_lpr_rate_view_sorts_by_success_rate() {
    let (_, body) = get("/api/player-analysis/defense-lpr?view=high_next_rate").await;
    assert_eq!(column(&body["rows"], "successes"), [14, 9]);
    assert_eq!(body["totals"]["successes"], 23);
    assert_eq!(body["totals"]["failures"], 13);
    assert!(
        body["rows"][0].get("xg_pct").is_none(),
        "xG fields left out"
    );

    let (status, _) = get("/api/player-analysis/defense-lpr?view=everything").await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}
