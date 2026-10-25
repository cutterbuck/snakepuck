-- Events credited to each stint.
--
-- An event is credited to the stint HALO assigned it to (events.game_stint),
-- which reflects the true order of plays around line changes. A few boundary
-- plays have no assignment; those go to the stint ending at that moment, since
-- the player who made the play was on the ice for it.
--
-- With legacy_parity, events are matched by time window [start, end) instead,
-- as the old pipeline did. That agrees with HALO's assignment everywhere except
-- the unassigned boundary plays, which it leaves uncredited.
--
-- On-ice xG counts every shot with xG while the player is on the ice:
-- for (xGF) when the shooting team is the player's team, against (xGA) otherwise.
-- Individual stats count only events the stint's player made.
with stints as (
    select game_id, game_stint, player_id, team_abbr, period, period_time_start, period_time_end
    from {{ ref('stg_halo__stints') }}
),

stint_windows as (
    select distinct game_id, game_stint, period, period_time_start, period_time_end
    from stints
),

events as (
    select game_id, sl_event_id, game_stint, period, period_time, player_id, team_abbr, event_type, outcome, xg
    from {{ ref('stg_halo__events') }}
    where xg is not null or event_type in ('goal', 'assist', 'shot', 'faceoff', 'block', 'check')
),

credited as (
    {% if var('legacy_parity') %}
    select events.* replace (w.game_stint as game_stint)
    from events
    inner join stint_windows as w
        on w.game_id = events.game_id
        and w.period = events.period
        and events.period_time >= w.period_time_start
        and events.period_time < w.period_time_end
    {% else %}
    select events.* replace (coalesce(events.game_stint, w.game_stint) as game_stint)
    from events
    left join stint_windows as w
        on events.game_stint is null
        and w.game_id = events.game_id
        and w.period = events.period
        and events.period_time > w.period_time_start
        and events.period_time <= w.period_time_end
    {% endif %}
),

on_ice_xg as (
    select
        s.game_id,
        s.game_stint,
        s.player_id,
        sum(if(e.team_abbr = s.team_abbr and e.player_id = s.player_id, e.xg, 0)) as i_xg,
        sum(if(e.team_abbr = s.team_abbr, e.xg, 0)) as oi_xgf,
        sum(if(e.team_abbr = s.team_abbr, 0, e.xg)) as oi_xga
    from stints as s
    inner join credited as e
        on e.game_id = s.game_id
        and e.game_stint = s.game_stint
    where e.xg is not null
    group by 1, 2, 3
),

individual as (
    select
        s.game_id,
        s.game_stint,
        s.player_id,
        countif(e.event_type = 'goal') as goals,
        countif(e.event_type = 'assist') as assists,
        countif(e.event_type in ('shot', 'goal')) as shots,
        countif(e.event_type = 'faceoff' and e.outcome = 'successful') as faceoffs_won,
        countif(e.event_type = 'faceoff' and e.outcome = 'failed') as faceoffs_lost,
        countif(e.event_type = 'block') as blocks,
        countif(e.event_type = 'check') as checks
    from stints as s
    inner join credited as e
        on e.game_id = s.game_id
        and e.game_stint = s.game_stint
        and e.player_id = s.player_id
    group by 1, 2, 3
)

select
    s.game_id,
    s.game_stint,
    s.player_id,
    round(coalesce(x.i_xg, 0), 3) as i_xg,
    round(coalesce(x.oi_xgf, 0), 3) as oi_xgf,
    round(coalesce(x.oi_xga, 0), 3) as oi_xga,
    coalesce(i.goals, 0) as goals,
    coalesce(i.assists, 0) as assists,
    coalesce(i.goals, 0) + coalesce(i.assists, 0) as points,
    coalesce(i.shots, 0) as shots,
    coalesce(i.faceoffs_won, 0) as faceoffs_won,
    coalesce(i.faceoffs_lost, 0) as faceoffs_lost,
    coalesce(i.blocks, 0) as blocks,
    coalesce(i.checks, 0) as checks
from stints as s
left join on_ice_xg as x using (game_id, game_stint, player_id)
left join individual as i using (game_id, game_stint, player_id)
