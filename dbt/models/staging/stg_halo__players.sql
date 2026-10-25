select
    player_id,
    player_name,
    first_name,
    last_name,
    handed,
    birth_date,
    position_group,
    primary_position
from {{ source('halo', 'players') }}
