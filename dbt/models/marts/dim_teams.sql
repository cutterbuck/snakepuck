-- One row per team: names, logo, division, and HALO's team id.
with source_ids as (
    select team_abbr, any_value(source_team_id) as source_team_id
    from (
        select home_team_abbr as team_abbr, home_source_team_id as source_team_id
        from {{ ref('stg_halo__games') }}
        union all
        select away_team_abbr, away_source_team_id
        from {{ ref('stg_halo__games') }}
    )
    group by 1
)

select
    teams.team_abbr,
    source_ids.source_team_id,
    teams.team_name,
    teams.division,
    'AHL' as league,
    teams.logo_url
from {{ ref('ahl_teams') }} as teams
inner join source_ids using (team_abbr)
