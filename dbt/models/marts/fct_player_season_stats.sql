-- One row per player per team per season (a traded player has a row per team).
--
-- Games played counts every game the player skated in; everything else rolls
-- up from fct_player_game_stats.
--
-- Only players with at least one event are included, as in the old pipeline.
-- (With legacy_parity, quiet games have no game row, so their on-ice xG and
-- ice time drop out while still counting toward games played.)
with seasons as (
    select distinct season_name from {{ ref('stg_halo__games') }}
),

-- Age is measured on the date of the last game in the data.
last_game as (
    select max(game_date) as last_game_date from {{ ref('stg_halo__games') }}
),

players_with_events as (
    select distinct player_id
    from {{ ref('stg_halo__events') }}
    where player_id is not null
),

games_played as (
    select
        player_id,
        team_abbr,
        any_value(source_team_id) as source_team_id,
        count(distinct game_id) as games_played
    from {{ ref('fct_stints') }}
    group by 1, 2
),

game_totals as (
    select
        player_id,
        team_abbr,
        sum(penalties) as penalties,
        sum(penalties_drawn) as penalties_drawn,
        {% for prefix in ['tot'] + situations() | map('first') | list %}
        {% for stat, kind in situational_stats().items() %}
        {% if kind == 'xg' %}
        round(sum({{ prefix }}_{{ stat }}), 3) as {{ prefix }}_{{ stat }},
        {% else %}
        sum({{ prefix }}_{{ stat }}) as {{ prefix }}_{{ stat }},
        {% endif %}
        {% endfor %}
        {% endfor %}
    from {{ ref('fct_player_game_stats') }}
    group by 1, 2
),

players as (
    select player_id, birth_date from {{ ref('stg_halo__players') }}
)

select
    gp.player_id,
    gp.source_team_id,
    gp.team_abbr,
    seasons.season_name as season,
    gp.games_played,
    coalesce(t.penalties, 0) as penalties,
    coalesce(t.penalties_drawn, 0) as penalties_drawn,
    date_diff(last_game.last_game_date, players.birth_date, year)
        - if(format_date('%m%d', last_game.last_game_date) < format_date('%m%d', players.birth_date), 1, 0)
        as age,
    {% for prefix in ['tot'] + situations() | map('first') | list %}
    {% for stat, kind in situational_stats().items() %}
    {% if kind == 'seconds' %}
    round(safe_divide(t.{{ prefix }}_{{ stat }}, gp.games_played), 1) as {{ prefix }}_atoi,
    {% else %}
    coalesce(t.{{ prefix }}_{{ stat }}, 0) as {{ prefix }}_{{ stat }},
    {% endif %}
    {% endfor %}
    round(safe_divide(t.{{ prefix }}_oi_xgf, t.{{ prefix }}_oi_xgf + t.{{ prefix }}_oi_xga), 3) as {{ prefix }}_xg_pct,
    round(safe_divide(t.{{ prefix }}_goals, t.{{ prefix }}_shots), 3) as {{ prefix }}_shooting_pct,
    round(
        safe_divide(t.{{ prefix }}_faceoffs_won, t.{{ prefix }}_faceoffs_won + t.{{ prefix }}_faceoffs_lost),
        3
    ) as {{ prefix }}_faceoff_pct,
    {% endfor %}
from games_played as gp
inner join players_with_events using (player_id)
left join game_totals as t using (player_id, team_abbr)
inner join players using (player_id)
cross join seasons
cross join last_game
