-- One row per game.
select
    game_id,
    game_date,
    league,
    season_name as season,
    home_team_abbr,
    away_team_abbr,
    home_source_team_id,
    away_source_team_id,
    home_score,
    away_score,
    game_outcome,
    home_start_net
from {{ ref('stg_halo__games') }}
