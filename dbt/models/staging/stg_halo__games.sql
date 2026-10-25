select
    game_id,
    game_date,
    league,
    season,
    format('%d-%02d', season, mod(season + 1, 100)) as season_name,
    home_team as home_team_abbr,
    away_team as away_team_abbr,
    home_team_id as home_source_team_id,
    away_team_id as away_source_team_id,
    home_score,
    away_score,
    game_outcome,
    home_start_net
from {{ source('halo', 'games') }}
