-- One row per player per stint, with stats split by game situation
-- (tot = all situations; es, ev5, pp, pk = only when the stint is in that situation).
with enriched as (
    select * from {{ ref('int_stints__enriched') }}
),

event_stats as (
    select * from {{ ref('int_stints__event_stats') }}
),

joined as (
    select
        enriched.*,
        event_stats.* except (game_id, game_stint, player_id)
    from enriched
    inner join event_stats using (game_id, game_stint, player_id)
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
    shift,
    {% for stat in situational_stats() %}
    {{ stat }} as tot_{{ stat }},
    {% endfor %}
    {% for prefix, flag in situations() %}
    {% for stat in situational_stats() %}
    if({{ flag }}, {{ stat }}, 0) as {{ prefix }}_{{ stat }},
    {% endfor %}
    {% endfor %}
from joined
