{{ config(enabled=not var('legacy_parity')) }}

-- Shifts account for every skater stint: same count and total ice time per
-- player-game, and no shift spans two periods.
with stint_totals as (
    select game_id, player_id, count(*) as n_stints, sum(tot_toi) as toi
    from {{ ref('fct_stints') }}
    where shift is not null
    group by 1, 2
),

shift_totals as (
    select game_id, player_id, sum(n_stints) as n_stints, sum(toi) as toi,
        countif(period is null) as missing_period
    from {{ ref('fct_shifts') }}
    group by 1, 2
),

multi_period as (
    select game_id, player_id, shift
    from {{ ref('fct_stints') }}
    where shift is not null
    group by 1, 2, 3
    having count(distinct period) > 1
)

select game_id, player_id, 'totals differ' as problem
from stint_totals
full outer join shift_totals using (game_id, player_id)
where stint_totals.n_stints is distinct from shift_totals.n_stints
    or abs(stint_totals.toi - shift_totals.toi) > 0.001
union all
select game_id, player_id, 'shift spans periods'
from multi_period
