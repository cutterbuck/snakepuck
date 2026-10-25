-- One row per player per game per team.
--
-- Stats roll up from fct_stints, so an event counts only if it falls inside one
-- of the player's stints. Penalties aren't tracked per stint and are counted
-- from events directly.
--
-- Parity with the old pipeline (fixed separately, see docs/MIGRATION_PLAN.md):
--   * A player gets a row only if they recorded at least one event for that
--     team in that game; quiet games are missing.
with games as (
    select game_id, season_name from {{ ref('stg_halo__games') }}
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
    e.penalties,
    e.penalties_drawn,
    s.* except (player_id, game_id, team_abbr, source_team_id),
    {% for prefix in ['tot'] + situations() | map('first') | list %}
    round(safe_divide(s.{{ prefix }}_goals, s.{{ prefix }}_shots), 3) as {{ prefix }}_shooting_pct,
    round(
        safe_divide(s.{{ prefix }}_faceoffs_won, s.{{ prefix }}_faceoffs_won + s.{{ prefix }}_faceoffs_lost),
        3
    ) as {{ prefix }}_faceoff_pct,
    {% endfor %}
from stint_totals as s
inner join event_totals as e using (player_id, game_id, team_abbr)
inner join games using (game_id)
