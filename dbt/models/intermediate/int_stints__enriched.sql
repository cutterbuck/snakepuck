-- Stints with game situation, time on ice, and shift number.
--
-- Situations are from the stint player's point of view:
--   even = equal skaters (5v5, 4v4, 3v3, ...), ev5 = 5v5 only,
--   pp = more skaters than the opponent, pk = fewer.
-- A shift is a run of consecutive stints with no gap (one stint ends exactly
-- when the next begins). Goalies have no shift number.
with stints as (
    select * from {{ ref('stg_halo__stints') }}
),

games as (
    select game_id, home_team_abbr from {{ ref('stg_halo__games') }}
),

players as (
    select player_id, primary_position from {{ ref('stg_halo__players') }}
),

sided as (
    select
        stints.*,
        players.primary_position,
        stints.team_abbr = games.home_team_abbr as is_home,
        if(stints.team_abbr = games.home_team_abbr, n_home_skaters, n_away_skaters) as own_skaters,
        if(stints.team_abbr = games.home_team_abbr, n_away_skaters, n_home_skaters) as opp_skaters
    from stints
    inner join games using (game_id)
    inner join players using (player_id)
),

shift_breaks as (
    select
        *,
        -- 1 when this stint starts a new shift (first stint, or a gap since the last one)
        if(
            lag(period_time_end) over player_game = period_time_start,
            0,
            1
        ) as starts_shift
    from sided
    window player_game as (partition by game_id, player_id order by game_stint)
)

select
    game_id,
    game_stint,
    player_id,
    team_abbr,
    source_team_id,
    period,
    period_time_start,
    period_time_end,
    n_home_skaters,
    n_away_skaters,
    is_home_net_empty,
    is_away_net_empty,
    home_score,
    away_score,
    is_home,
    n_home_skaters = n_away_skaters as is_even,
    n_home_skaters = n_away_skaters and n_home_skaters = 5 as is_5v5,
    own_skaters > opp_skaters as is_pp,
    own_skaters < opp_skaters as is_pk,
    period_time_end - period_time_start as toi,
    if(
        primary_position != 'G',
        sum(starts_shift) over (
            partition by game_id, player_id
            order by game_stint
            rows between unbounded preceding and current row
        ),
        null
    ) as shift
from shift_breaks
