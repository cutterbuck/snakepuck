{{ config(cluster_by=['game_id', 'period']) }}

-- One row per event, with what the game-report rink displays.
select
    game_id,
    sl_event_id,
    sequence_id,
    period,
    period_time,
    game_stint,
    player_id,
    team_abbr,
    opp_team_abbr,
    lower(coalesce(event_type, 'unknown')) as event_type,
    outcome,
    flags,
    description,
    detail,
    xg,
    x,
    y,
    has_tracking_data
from {{ ref('stg_halo__events') }}
