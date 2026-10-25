-- Every counted player event is credited to one of that player's stints.
-- One faceoff is a known data glitch: its player isn't on the ice in the stint
-- HALO assigned it to, or in any stint at that time.
{{ config(enabled=not var('legacy_parity'), error_if='>1', warn_if='>1') }}

with credited as (
    select sum(tot_goals) as goals, sum(tot_shots) as shots,
        sum(tot_faceoffs_won + tot_faceoffs_lost) as faceoffs, sum(tot_blocks) as blocks,
        sum(tot_checks) as checks, sum(tot_assists) as assists
    from {{ ref('fct_stints') }}
),

events as (
    select
        countif(event_type = 'goal') as goals,
        countif(event_type in ('shot', 'goal')) as shots,
        countif(event_type = 'faceoff' and outcome in ('successful', 'failed')) as faceoffs,
        countif(event_type = 'block') as blocks,
        countif(event_type = 'check') as checks,
        countif(event_type = 'assist') as assists
    from {{ ref('stg_halo__events') }}
    where player_id is not null
)

select stat, events_n - credited_n as uncredited
from credited, events,
    unnest([
        struct('goals' as stat, events.goals as events_n, credited.goals as credited_n),
        ('shots', events.shots, credited.shots),
        ('faceoffs', events.faceoffs, credited.faceoffs),
        ('blocks', events.blocks, credited.blocks),
        ('checks', events.checks, credited.checks),
        ('assists', events.assists, credited.assists)
    ])
cross join unnest(generate_array(1, abs(events_n - credited_n)))
