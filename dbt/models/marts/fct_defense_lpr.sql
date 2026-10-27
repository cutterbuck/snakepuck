-- One row per defenseman per view of the Player Analysis page's LPR table:
--
--   low, high            on-ice xG after low- or high-pressure LPRs
--   high_next_success    ... after high-pressure LPRs whose next play succeeded
--   high_next_failure    ... after high-pressure LPRs whose next play didn't
--   high_next_rate       next-play success rate after high-pressure LPRs
--
-- The xG views count only LPRs with a shift to measure (post-LPR xG not null); the
-- rate view counts every high-pressure LPR. Every defenseman with at least one LPR in
-- a view gets a row; the page's minimums (20 GP, 15 LPRs) are applied by the API.
{% set xg_views = {
    'low': "pressure = 'low'",
    'high': "pressure = 'high'",
    'high_next_success': "pressure = 'high' and next_play_success",
    'high_next_failure': "pressure = 'high' and not next_play_success",
} %}

with lprs as (
    select * from {{ ref('int_lpr_events') }}
),

games_played as (
    select player_id, sum(games_played) as games_played
    from {{ ref('fct_player_season_stats') }}
    group by 1
),

views as (
    {% for view, condition in xg_views.items() %}
    select
        player_id,
        '{{ view }}' as view,
        count(*) as lpr_count,
        sum(post_lpr_oi_xgf) as total_oi_xgf,
        sum(post_lpr_oi_xga) as total_oi_xga,
        cast(null as int64) as successes,
        cast(null as int64) as failures
    from lprs
    where {{ condition }} and post_lpr_oi_xgf is not null
    group by 1
    union all
    {% endfor %}
    select
        player_id,
        'high_next_rate' as view,
        count(*) as lpr_count,
        null as total_oi_xgf,
        null as total_oi_xga,
        countif(next_play_success) as successes,
        countif(not next_play_success) as failures
    from lprs
    where pressure = 'high'
    group by 1
)

select
    views.player_id,
    views.view,
    coalesce(games_played.games_played, 0) as games_played,
    views.lpr_count,
    views.total_oi_xgf / views.lpr_count as avg_oi_xgf,
    views.total_oi_xga / views.lpr_count as avg_oi_xga,
    views.total_oi_xgf,
    views.total_oi_xga,
    safe_divide(views.total_oi_xgf, views.total_oi_xgf + views.total_oi_xga) as xg_pct,
    views.successes,
    views.failures,
    views.successes / views.lpr_count as success_rate
from views
left join games_played using (player_id)
