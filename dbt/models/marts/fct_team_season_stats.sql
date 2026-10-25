-- Standings: one row per team per season.
-- Wins are worth 2 points; overtime and shootout losses are worth 1.
with games as (
    select * from {{ ref('stg_halo__games') }}
),

team_games as (
    select
        season_name,
        home_team_abbr as team_abbr,
        home_source_team_id as source_team_id,
        home_score as goals_for,
        away_score as goals_against,
        starts_with(game_outcome, 'home') as won,
        game_outcome
    from games
    union all
    select
        season_name,
        away_team_abbr,
        away_source_team_id,
        away_score,
        home_score,
        starts_with(game_outcome, 'away'),
        game_outcome
    from games
),

results as (
    select
        *,
        game_outcome like '%_ot_%' as is_overtime,
        game_outcome like '%_so_%' as is_shootout,
        not (game_outcome like '%_ot_%' or game_outcome like '%_so_%') as is_regulation
    from team_games
),

totals as (
    select
        team_abbr,
        any_value(source_team_id) as source_team_id,
        season_name as season,
        count(*) as games_played,
        countif(won) as wins,
        countif(not won and is_regulation) as losses,
        countif(not won and not is_regulation) as ot_losses,
        2 * countif(won) + countif(not won and not is_regulation) as points,
        countif(won and is_regulation) as regulation_wins,
        countif(won and not is_shootout) as regulation_or_ot_wins,
        sum(goals_for) as goals_forward,
        sum(goals_against) as goals_against,
        countif(won and is_shootout) as so_wins,
        countif(not won and is_shootout) as so_losses
    from results
    group by team_abbr, season_name
)

select
    totals.source_team_id,
    totals.team_abbr,
    totals.season,
    teams.division,
    totals.games_played,
    totals.wins,
    totals.losses,
    totals.ot_losses,
    totals.points,
    round(safe_divide(totals.points, 2 * totals.games_played), 3) as points_percentage,
    totals.regulation_wins,
    totals.regulation_or_ot_wins,
    totals.goals_forward,
    totals.goals_against,
    totals.goals_forward - totals.goals_against as goal_diff,
    format('%d-%d', totals.so_wins, totals.so_losses) as so_record
from totals
inner join {{ ref('ahl_teams') }} as teams using (team_abbr)
