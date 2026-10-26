{{ config(cluster_by=['game_id', 'player_id']) }}

-- One row per skater shift: consecutive stints with no gap between them.
-- Goalies have no shifts.
with stints as (
    select * from {{ ref('fct_stints') }}
    where shift is not null
),

first_stints as (
    -- Game state shown for a shift is the state when it began.
    select * from stints
    qualify row_number() over (partition by game_id, player_id, shift order by game_stint) = 1
)

select
    s.game_id,
    s.player_id,
    s.shift,
    any_value(s.team_abbr) as team_abbr,
    any_value(s.period) as period,
    min(s.game_stint) as first_game_stint,
    max(s.game_stint) as last_game_stint,
    count(*) as n_stints,
    min(s.period_time_start) as period_time_start,
    max(s.period_time_end) as period_time_end,
    sum(s.tot_toi) as toi,
    any_value(f.n_home_skaters) as n_home_skaters,
    any_value(f.n_away_skaters) as n_away_skaters,
    any_value(f.is_home_net_empty) as is_home_net_empty,
    any_value(f.is_away_net_empty) as is_away_net_empty,
    any_value(f.home_score) as home_score,
    any_value(f.away_score) as away_score,
    round(sum(s.tot_i_xg), 3) as i_xg,
    round(sum(s.tot_oi_xgf), 3) as oi_xgf,
    round(sum(s.tot_oi_xga), 3) as oi_xga
from stints as s
inner join first_stints as f using (game_id, player_id, shift)
group by 1, 2, 3
