-- One row per player per game per team.
--
-- Stats roll up from fct_stints: every game the player skated in gets a row.
-- Penalties aren't tracked per stint and are counted from events directly.
--
-- With legacy_parity, a player gets a row only if they recorded at least one
-- event for that team in that game, as in the old pipeline (quiet games missing).
with games as (
    select game_id, season_name, home_team_abbr, away_team_abbr, home_score, away_score, game_outcome
    from {{ ref('stg_halo__games') }}
),

event_totals as (
    select
        player_id,
        game_id,
        team_abbr,
        countif(event_type = 'penalty') as penalties,
        countif(event_type = 'penaltydrawn') as penalties_drawn
    from {{ ref('stg_halo__events') }}
    where player_id is not null
    group by 1, 2, 3
),

stint_totals as (
    select
        player_id,
        game_id,
        team_abbr,
        any_value(source_team_id) as source_team_id,
        {% for prefix in ['tot'] + situations() | map('first') | list %}
        {% for stat, kind in situational_stats().items() %}
        {% if kind == 'xg' %}
        round(sum({{ prefix }}_{{ stat }}), 3) as {{ prefix }}_{{ stat }},
        {% else %}
        sum({{ prefix }}_{{ stat }}) as {{ prefix }}_{{ stat }},
        {% endif %}
        {% endfor %}
        {% endfor %}
    from {{ ref('fct_stints') }}
    group by 1, 2, 3
)

select
    s.player_id,
    s.game_id,
    s.source_team_id,
    s.team_abbr,
    games.season_name as season,
    s.team_abbr = games.home_team_abbr as is_home,
    if(s.team_abbr = games.home_team_abbr, games.away_team_abbr, games.home_team_abbr) as opp_team_abbr,
    if(s.team_abbr = games.home_team_abbr, games.home_score, games.away_score) as team_score,
    if(s.team_abbr = games.home_team_abbr, games.away_score, games.home_score) as opp_score,
    -- W/L, with OT or SO prefixed when the game went past regulation: W, OTW, SOW, L, OTL, SOL.
    concat(
        case
            when strpos(games.game_outcome, '_ot_') > 0 then 'OT'
            when strpos(games.game_outcome, '_so_') > 0 then 'SO'
            else ''
        end,
        if(starts_with(games.game_outcome, if(s.team_abbr = games.home_team_abbr, 'home', 'away')), 'W', 'L')
    ) as result,
    coalesce(e.penalties, 0) as penalties,
    coalesce(e.penalties_drawn, 0) as penalties_drawn,
    s.* except (player_id, game_id, team_abbr, source_team_id),
    {% for prefix in ['tot'] + situations() | map('first') | list %}
    round(safe_divide(s.{{ prefix }}_oi_xgf, s.{{ prefix }}_oi_xgf + s.{{ prefix }}_oi_xga), 3) as {{ prefix }}_xg_pct,
    round(safe_divide(s.{{ prefix }}_goals, s.{{ prefix }}_shots), 3) as {{ prefix }}_shooting_pct,
    round(
        safe_divide(s.{{ prefix }}_faceoffs_won, s.{{ prefix }}_faceoffs_won + s.{{ prefix }}_faceoffs_lost),
        3
    ) as {{ prefix }}_faceoff_pct,
    {% endfor %}
from stint_totals as s
{{ 'inner' if var('legacy_parity') else 'left' }} join event_totals as e using (player_id, game_id, team_abbr)
inner join games using (game_id)
