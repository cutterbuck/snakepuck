-- One row per player.
select
    player_id,
    first_name,
    last_name,
    coalesce(first_name || ' ' || last_name, player_name) as full_name,
    primary_position,
    position_group,
    handed,
    birth_date
from {{ ref('stg_halo__players') }}
