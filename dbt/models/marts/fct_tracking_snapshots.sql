{{ config(cluster_by=['game_id', 'sl_event_id']) }}

-- Skater positions at each event, ready for the game-report rink: one row per
-- skater per event, with the event's clock time and a display name.
-- Skaters HALO couldn't identify keep their team and position and are labelled
-- "Unidentified (<team>)".
with tracking as (
    select * from {{ ref('stg_halo__tracking') }}
    where tracking_x is not null and tracking_y is not null
),

events as (
    select game_id, sl_event_id, period, period_time from {{ ref('stg_halo__events') }}
),

games as (
    select game_id, home_source_team_id, home_team_abbr, away_source_team_id, away_team_abbr
    from {{ ref('stg_halo__games') }}
),

players as (
    select player_id, first_name, last_name from {{ ref('stg_halo__players') }}
)

select
    t.game_id,
    t.sl_event_id,
    events.period,
    events.period_time,
    t.source_team_id,
    case t.source_team_id
        when games.home_source_team_id then games.home_team_abbr
        when games.away_source_team_id then games.away_team_abbr
    end as team_abbr,
    t.player_id,
    players.last_name,
    coalesce(
        players.first_name || ' ' || players.last_name,
        t.player_name,
        'Unidentified (' || coalesce(t.team_name, 'unknown team') || ')'
    ) as display_name,
    t.tracking_x,
    t.tracking_y,
    t.tracking_vel_x,
    t.tracking_vel_y
from tracking as t
inner join events using (game_id, sl_event_id)
inner join games using (game_id)
left join players using (player_id)
