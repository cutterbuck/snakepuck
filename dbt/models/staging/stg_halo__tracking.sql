-- Skater positions at each event (a snapshot per event, not continuous frames).
-- About 31% of rows have no player_id: the skater's team and position are known,
-- but not who they are.
select
    game_id,
    sl_event_id,
    player_id,
    player_name,
    team_id as source_team_id,
    team_name,
    tracking_x,
    tracking_y,
    tracking_vel_x,
    tracking_vel_y
from {{ source('halo', 'tracking') }}
