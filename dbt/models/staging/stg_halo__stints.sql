-- One row per player per stint (a stretch of play with no line change).
select
    game_id,
    game_stint,
    player_id,
    player_name,
    team as team_abbr,
    team_id as source_team_id,
    period,
    cast(period_time_start as float64) as period_time_start,
    cast(period_time_end as float64) as period_time_end,
    n_home_skaters,
    n_away_skaters,
    is_home_net_empty,
    is_away_net_empty,
    home_score,
    away_score
from {{ source('halo', 'stints') }}
