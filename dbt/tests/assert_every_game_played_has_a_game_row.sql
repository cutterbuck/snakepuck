-- Every game a player skated in has a player-game row, even with no events.
{{ config(enabled=not var('legacy_parity')) }}

select distinct s.player_id, s.game_id, s.team_abbr
from {{ ref('fct_stints') }} as s
left join {{ ref('fct_player_game_stats') }} as g using (player_id, game_id, team_abbr)
where g.player_id is null
