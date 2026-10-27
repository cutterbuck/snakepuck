-- One row per loose puck recovery (LPR) by a defenseman at 5-on-5, with what followed
-- it. This is the logic of the Dash Player Analysis page, which ran it per request:
--
--   pressure    HALO's "HI PRESS" dump-in recoveries are high; "DUMP IN LPR+" is low.
--   5-on-5      the LPR's stint has five skaters a side.
--   next play   the same player's later events in the same period, within 5 s
--               (ties at the same instant ordered by event id). Successful if any is a
--               successful pass, puck protection, dump-out, assist, drawn penalty or
--               controlled breakout, and none is a failed pass location.
--   post-LPR xG the player's on-ice xGF and xGA from the LPR's stint to the end of
--               his shift, stopping after the first stint with a faceoff. Null when he
--               has no stint with a shift at that moment.
{% set success_types = ['pass', 'puckprotection', 'dumpout', 'assist', 'penaltydrawn', 'controlledbreakout'] %}

with defensemen as (
    select player_id from {{ ref('stg_halo__players') }}
    where primary_position = 'D'
),

events as (
    select game_id, sl_event_id, player_id, period, period_time, game_stint, event_type, outcome, description
    from {{ ref('stg_halo__events') }}
),

stints as (
    select game_id, game_stint, player_id, shift, n_home_skaters, n_away_skaters, tot_oi_xgf, tot_oi_xga
    from {{ ref('fct_stints') }}
),

five_on_five as (
    select distinct game_id, game_stint
    from stints
    where n_home_skaters = 5 and n_away_skaters = 5
),

lprs as (
    select
        events.*,
        if(events.description = 'DUMP IN LPR+', 'low', 'high') as pressure
    from events
    inner join defensemen using (player_id)
    inner join five_on_five using (game_id, game_stint)
    where
        events.event_type = 'lpr'
        and events.description in ('DUMP IN LPR+', 'HI PRESS DUMP IN LPR+', 'CONT HI PRESS DUMP IN LPR+')
),

next_plays as (
    select
        lprs.game_id,
        lprs.sl_event_id,
        logical_or(
            later.event_type in ('{{ success_types | join("', '") }}') and later.outcome = 'successful'
        ) as has_success,
        logical_or(later.event_type = 'failedpasslocation') as has_failure
    from lprs
    inner join events as later
        on
            later.game_id = lprs.game_id
            and later.player_id = lprs.player_id
            and later.period = lprs.period
            and (
                later.period_time > lprs.period_time
                or (later.period_time = lprs.period_time and later.sl_event_id > lprs.sl_event_id)
            )
            and later.period_time - lprs.period_time <= 5.0
    group by 1, 2
),

faceoff_stints as (
    select distinct game_id, game_stint
    from events
    where event_type = 'faceoff'
),

-- The player's stints from the LPR's to the end of his shift.
rest_of_shift as (
    select
        lprs.game_id,
        lprs.sl_event_id,
        later.game_stint,
        later.tot_oi_xgf,
        later.tot_oi_xga,
        faceoff_stints.game_stint is not null as has_faceoff
    from lprs
    inner join stints as at_lpr
        on
            at_lpr.game_id = lprs.game_id
            and at_lpr.player_id = lprs.player_id
            and at_lpr.game_stint = lprs.game_stint
            and at_lpr.shift is not null
    inner join stints as later
        on
            later.game_id = lprs.game_id
            and later.player_id = lprs.player_id
            and later.shift = at_lpr.shift
            and later.game_stint >= lprs.game_stint
    left join faceoff_stints
        on faceoff_stints.game_id = later.game_id and faceoff_stints.game_stint = later.game_stint
),

post_lpr as (
    select
        game_id,
        sl_event_id,
        sum(tot_oi_xgf) as post_lpr_oi_xgf,
        sum(tot_oi_xga) as post_lpr_oi_xga
    from (
        select
            *,
            min(if(has_faceoff, game_stint, null)) over (partition by game_id, sl_event_id) as first_faceoff_stint
        from rest_of_shift
    )
    where first_faceoff_stint is null or game_stint <= first_faceoff_stint
    group by 1, 2
)

select
    lprs.game_id,
    lprs.sl_event_id,
    lprs.player_id,
    lprs.period,
    lprs.period_time,
    lprs.game_stint,
    lprs.pressure,
    coalesce(next_plays.has_success, false) and not coalesce(next_plays.has_failure, false) as next_play_success,
    post_lpr.post_lpr_oi_xgf,
    post_lpr.post_lpr_oi_xga
from lprs
left join next_plays using (game_id, sl_event_id)
left join post_lpr using (game_id, sl_event_id)
